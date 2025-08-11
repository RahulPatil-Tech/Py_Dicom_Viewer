"""
pro_dicom_viewer.py

Matplotlib-based DICOM viewer (fixed recursion bug):
- Slider + mouse wheel + keyboard navigation
- WW/WL sliders (interactive windowing)
- Metadata panel
- Zoom/pan, save PNG, ROI measurement
- Programmatic slider updates guarded to prevent recursion
"""

import os
import sys
import math
import pydicom
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from matplotlib.patches import Rectangle

# ---------- Utilities ----------
def load_dicom_series(directory):
    files = []
    for fname in os.listdir(directory):
        if fname.lower().endswith(".dcm") or fname.lower().endswith(".dicom"):
            files.append(os.path.join(directory, fname))
    if not files:
        raise FileNotFoundError(f"No DICOM files found in {directory}")
    datasets = []
    for f in files:
        try:
            ds = pydicom.dcmread(f, force=True)
            datasets.append((f, ds))
        except Exception as e:
            print(f"Warning: couldn't read {f}: {e}", file=sys.stderr)

    def sort_key(item):
        f, ds = item
        inst = getattr(ds, "InstanceNumber", None)
        ipp = getattr(ds, "ImagePositionPatient", None)
        if inst is not None:
            try:
                return (0, int(inst))
            except Exception:
                pass
        if ipp is not None and len(ipp) >= 3:
            try:
                return (1, float(ipp[2]))
            except Exception:
                pass
        return (2, os.path.basename(f))
    datasets.sort(key=sort_key)
    return [ds for f, ds in datasets]

def get_image_array(ds):
    arr = ds.pixel_array.astype(np.float32)
    slope = float(getattr(ds, "RescaleSlope", 1.0))
    intercept = float(getattr(ds, "RescaleIntercept", 0.0))
    return arr * slope + intercept

def apply_window_level(arr, wl, ww):
    low = wl - (ww / 2.0)
    high = wl + (ww / 2.0)
    clipped = np.clip(arr, low, high)
    norm = (clipped - low) / (high - low)
    return norm

def format_patient_name(ds):
    try:
        return str(ds.PatientName)
    except Exception:
        return "Unknown"

# ---------- Viewer ----------
class DicomViewer:
    def __init__(self, directory):
        self.directory = directory
        self.datasets = load_dicom_series(directory)
        self.images = [get_image_array(ds) for ds in self.datasets]
        self.n = len(self.images)
        if self.n == 0:
            raise RuntimeError("No images loaded")
        self.index = 0
        first = self.datasets[0]
        wc = getattr(first, "WindowCenter", None)
        ww = getattr(first, "WindowWidth", None)
        if isinstance(wc, (list, tuple)): wc = wc[0]
        if isinstance(ww, (list, tuple)): ww = ww[0]
        try:
            self.wl = float(wc) if wc is not None else float(np.mean(self.images[0]))
            self.ww = float(ww) if ww is not None else (np.max(self.images[0]) - np.min(self.images[0]) or 1.0)
        except Exception:
            self.wl = float(np.mean(self.images[0]))
            self.ww = float(np.ptp(self.images[0]) or 1.0)

        self.pixel_spacing = self._get_pixel_spacing(first)
        self.roi_points = []
        self.roi_patch = None
        self.dist_text = None
        self._measuring = False

        self.playing = False
        self.play_interval = 200  # ms

        # guard to ignore slider-driven recursion
        self._ignore_slider_callback = False

        # build UI
        self._build_figure()
        self._connect_events()
        self._update_display(initial=True)

    def _get_pixel_spacing(self, ds):
        ps = getattr(ds, "PixelSpacing", None)
        if ps is None and hasattr(ds, "ImagerPixelSpacing"):
            ps = getattr(ds, "ImagerPixelSpacing")
        if ps is None:
            return (1.0, 1.0)
        try:
            return (float(ps[0]), float(ps[1]))
        except Exception:
            try:
                val = float(ps)
                return (val, val)
            except Exception:
                return (1.0, 1.0)

    def _build_figure(self):
        self.fig, self.ax = plt.subplots(figsize=(9, 8))
        plt.subplots_adjust(left=0.25, bottom=0.30, right=0.78)
        img0 = apply_window_level(self.images[0], self.wl, self.ww)
        self.display = self.ax.imshow(img0, cmap=plt.cm.bone, origin='lower')# type:ignore
        self.ax.set_title(self._title_text())

        # metadata axis
        self.meta_ax = self.fig.add_axes([0.82, 0.05, 0.16, 0.90]) # type:ignore
        self.meta_ax.axis('off')
        self.meta_text = self.meta_ax.text(0.0, 1.0, "", va='top', wrap=True, fontsize=9)

        # controls
        axcolor = 'lightgoldenrodyellow'
        ax_index = self.fig.add_axes([0.25, 0.20, 0.50, 0.03], facecolor=axcolor)# type:ignore
        self.s_index = Slider(ax_index, 'Image', 1, max(1, self.n), valinit=1, valfmt='%0.0f', valstep=1)

        global_min = float(np.min(self.images))
        global_max = float(np.max(self.images))
        span = global_max - global_min
        ax_ww = self.fig.add_axes([0.25, 0.14, 0.50, 0.03], facecolor=axcolor)# type:ignore
        ax_wl = self.fig.add_axes([0.25, 0.08, 0.50, 0.03], facecolor=axcolor)# type:ignore
        self.s_ww = Slider(ax_ww, 'WW', max(1.0, span/100.0), max(1.0, span*2.0), valinit=max(1.0, self.ww))
        self.s_wl = Slider(ax_wl, 'WL', global_min - span, global_max + span, valinit=self.wl)

        ax_save = self.fig.add_axes([0.05, 0.9, 0.12, 0.06])# type:ignore
        ax_play = self.fig.add_axes([0.05, 0.82, 0.12, 0.06])# type:ignore
        ax_roi  = self.fig.add_axes([0.05, 0.74, 0.12, 0.06])# type:ignore
        self.b_save = Button(ax_save, 'Save PNG')
        self.b_play = Button(ax_play, 'Play')
        self.b_roi  = Button(ax_roi, 'Measure')

    def _connect_events(self):
        self.s_index.on_changed(self._on_index_slider)
        self.s_ww.on_changed(self._on_window_slider)
        self.s_wl.on_changed(self._on_window_slider)
        self.b_save.on_clicked(self._on_save)
        self.b_play.on_clicked(self._on_play_pause)
        self.b_roi.on_clicked(self._on_roi_button)
        self.fig.canvas.mpl_connect('scroll_event', self._on_scroll)
        self.fig.canvas.mpl_connect('key_press_event', self._on_key)
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)
        self.fig.canvas.mpl_connect('close_event', lambda ev: setattr(self, "playing", False))

    # ---------- Index management (centralized) ----------
    def set_index(self, new_index):
        """Set index (0-based) and update UI. Use this for programmatic changes."""
        new_index = max(0, min(self.n - 1, int(new_index)))
        self.index = new_index
        # update slider programmatically while ignoring its callback to avoid recursion
        try:
            self._ignore_slider_callback = True
            self.s_index.set_val(self.index + 1)
        finally:
            self._ignore_slider_callback = False
        self._update_display()

    # ---------- Event handlers ----------
    def _on_index_slider(self, val):
        if self._ignore_slider_callback:
            return
        # user moved slider: update index and display
        self.index = int(self.s_index.val) - 1
        self._update_display()

    def _on_window_slider(self, val):
        self.ww = float(self.s_ww.val)
        self.wl = float(self.s_wl.val)
        self._update_display()

    def _on_save(self, event):
        fname = f"dicom_slice_{self.index+1}.png"
        self.fig.savefig(fname, dpi=150, bbox_inches='tight')
        print(f"Saved current view to {fname}")

    def _on_play_pause(self, event):
        self.playing = not self.playing
        self.b_play.label.set_text('Pause' if self.playing else 'Play')
        if self.playing:
            self._play_step()

    def _play_step(self):
        if not self.playing:
            return
        next_idx = (self.index + 1) % self.n
        # use set_index so slider update is guarded
        self.set_index(next_idx)
        timer = self.fig.canvas.new_timer(interval=self.play_interval)
        timer.add_callback(self._play_step)
        timer.start()

    def _on_scroll(self, event):
        if event.inaxes != self.ax:
            return
        if event.button == 'up':
            self.set_index(self.index + 1)
        else:
            self.set_index(self.index - 1)

    def _on_key(self, event):
        if event.key in ['right', 'l']:
            self.set_index(self.index + 1)
        elif event.key in ['left', 'h']:
            self.set_index(self.index - 1)
        elif event.key == '+':
            cur_xlim = self.ax.get_xlim()
            cur_ylim = self.ax.get_ylim()
            self.ax.set_xlim(cur_xlim[0]*0.9 + cur_xlim[1]*0.1, cur_xlim[0]*0.1 + cur_xlim[1]*0.9)
            self.ax.set_ylim(cur_ylim[0]*0.9 + cur_ylim[1]*0.1, cur_ylim[0]*0.1 + cur_ylim[1]*0.9)
            self.fig.canvas.draw_idle()
        elif event.key == '-':
            cur_xlim = self.ax.get_xlim()
            cur_ylim = self.ax.get_ylim()
            dx = cur_xlim[1] - cur_xlim[0]
            dy = cur_ylim[1] - cur_ylim[0]
            center_x = 0.5*(cur_xlim[0] + cur_xlim[1])
            center_y = 0.5*(cur_ylim[0] + cur_ylim[1])
            self.ax.set_xlim(center_x - dx*1.1/2.0, center_x + dx*1.1/2.0)
            self.ax.set_ylim(center_y - dy*1.1/2.0, center_y + dy*1.1/2.0)
            self.fig.canvas.draw_idle()

    def _on_click(self, event):
        if event.inaxes != self.ax:
            return
        if event.button == 1:
            if self._measuring and len(self.roi_points) < 2:
                self.roi_points.append((event.xdata, event.ydata))
                if len(self.roi_points) == 2:
                    self._show_roi()
        elif event.button == 3:
            self._clear_roi()

    def _on_roi_button(self, event):
        self._measuring = not self._measuring
        self.roi_points = []
        self._clear_roi()
        self.b_roi.label.set_text("Measuring" if self._measuring else "Measure")
        print("Measuring:", self._measuring)

    # ---------- Display updates ----------
    def _title_text(self):
        return f"DICOM: {os.path.basename(self.directory)}  [{self.index+1}/{self.n}]"

    def _update_display(self, initial=False):
        arr = self.images[self.index]
        img_norm = apply_window_level(arr, self.wl, self.ww)
        self.display.set_data(img_norm)
        self.display.set_clim(0, 1)
        self.ax.set_title(self._title_text())
        ds = self.datasets[self.index]
        text = [
            f"Patient: {format_patient_name(ds)}",
            f"ID: {getattr(ds, 'PatientID', 'N/A')}",
            f"Study Date: {getattr(ds, 'StudyDate', 'N/A')}",
            f"Modality: {getattr(ds, 'Modality', 'N/A')}",
            f"Slice: {self.index+1}/{self.n}",
            f"Pixel Spacing: {self.pixel_spacing[0]} x {self.pixel_spacing[1]} mm"
        ]
        if hasattr(ds, 'SliceLocation'):
            text.append(f"SliceLocation: {getattr(ds, 'SliceLocation')}")
        if hasattr(ds, 'InstanceNumber'):
            text.append(f"InstanceNumber: {getattr(ds, 'InstanceNumber')}")
        self.meta_text.set_text("\n".join(text))
        if len(self.roi_points) == 2:
            self._show_roi()
        else:
            if self.roi_patch:
                try: self.roi_patch.remove()
                except Exception: pass
                self.roi_patch = None
            if self.dist_text:
                try: self.dist_text.remove()
                except Exception: pass
                self.dist_text = None
        if initial:
            self.fig.canvas.draw()
        else:
            self.fig.canvas.draw_idle()

    # ---------- ROI ----------
    def _clear_roi(self):
        self.roi_points = []
        if self.roi_patch:
            try: self.roi_patch.remove()
            except Exception: pass
            self.roi_patch = None
        if self.dist_text:
            try: self.dist_text.remove()
            except Exception: pass
            self.dist_text = None
        self.fig.canvas.draw_idle()

    def _show_roi(self):
        if len(self.roi_points) < 2:
            return
        (x1, y1), (x2, y2) = self.roi_points
        dx_pix = (x2 - x1)
        dy_pix = (y2 - y1)
        ps_row, ps_col = self.pixel_spacing
        dist_mm = math.hypot(dx_pix * ps_col, dy_pix * ps_row)
        x_min = min(x1, x2); y_min = min(y1, y2)
        width = abs(x2 - x1); height = abs(y2 - y1)
        if self.roi_patch:
            try: self.roi_patch.remove()
            except Exception: pass
        self.roi_patch = Rectangle((x_min, y_min), width, height,
                                   edgecolor='red', facecolor='none', linewidth=1.5)
        self.ax.add_patch(self.roi_patch)
        if self.dist_text:
            try: self.dist_text.remove()
            except Exception: pass
        self.dist_text = self.ax.text(x_min, y_min - 5, f"{dist_mm:.2f} mm", color='yellow', fontsize=9,
                                      bbox=dict(facecolor='black', alpha=0.5))
        self.fig.canvas.draw_idle()
        print(f"ROI distance: {dist_mm:.2f} mm")

    # ---------- Optional MP4 export ----------
    def export_mp4(self, outpath="series.mp4", fps=10):
        try:
            import imageio
        except ImportError:
            print("imageio not installed.")
            return
        frames = []
        for i in range(self.n):
            arr = apply_window_level(self.images[i], self.wl, self.ww)
            frame = (255.0 * arr).astype(np.uint8)
            frames.append(frame)
        imageio.mimwrite(outpath, frames, fps=fps)
        print(f"Exported to {outpath}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Pro DICOM viewer (fixed)")
    parser.add_argument('directory', nargs='?', default=None, help="Directory with DICOM files")
    args = parser.parse_args()
    if args.directory is None:
        default = "/media/rp32/0E3F-0E06/HCI Project/series-00000"
        print("No directory provided. Using default:", default)
        directory = default
    else:
        directory = args.directory
    if not os.path.isdir(directory):
        print("Directory does not exist:", directory)
        sys.exit(1)
    viewer = DicomViewer(directory)
    plt.show()

if __name__ == "__main__":
    main()

