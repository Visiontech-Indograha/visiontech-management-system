/**
 * Matematika zoom & geser (pan) foto K3 tanpa React. Skala 1x-4x; posisi (x, y) dalam piksel CSS
 * relatif ke pusat area tampil. Dipakai oleh molecule ZoomableImage dan diuji terpisah.
 */

export const ZOOM_MIN = 1;
export const ZOOM_MAX = 4;
export const ZOOM_DOUBLE_TAP = 2;

export interface ZoomState {
  scale: number;
  x: number;
  y: number;
}

export const ZOOM_RESET: ZoomState = { scale: 1, x: 0, y: 0 };

export function clampScale(scale: number): number {
  if (!Number.isFinite(scale)) return ZOOM_MIN;
  return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, scale));
}

/** Batas geser: gambar yang diperbesar tidak boleh digeser melewati tepi area tampil. */
export function clampPan(state: ZoomState, view: { width: number; height: number }): ZoomState {
  const maxX = Math.max(0, ((view.width * state.scale) - view.width) / 2);
  const maxY = Math.max(0, ((view.height * state.scale) - view.height) / 2);
  return {
    scale: state.scale,
    x: Math.min(maxX, Math.max(-maxX, state.x)),
    y: Math.min(maxY, Math.max(-maxY, state.y)),
  };
}

/**
 * Ubah skala dengan titik fokus (anchor) tetap di bawah kursor/jari. `anchor` relatif ke pusat area.
 */
export function zoomAround(
  state: ZoomState,
  nextScale: number,
  anchor: { x: number; y: number },
  view: { width: number; height: number },
): ZoomState {
  const scale = clampScale(nextScale);
  if (scale === ZOOM_MIN) return { scale, x: 0, y: 0 };
  const ratio = scale / state.scale;
  const next = {
    scale,
    x: anchor.x - (anchor.x - state.x) * ratio,
    y: anchor.y - (anchor.y - state.y) * ratio,
  };
  return clampPan(next, view);
}

/** Ketuk dua kali: 1x ↔ 2x dengan titik fokus di ketukan. */
export function doubleTapZoom(
  state: ZoomState,
  anchor: { x: number; y: number },
  view: { width: number; height: number },
): ZoomState {
  return zoomAround(state, state.scale > ZOOM_MIN ? ZOOM_MIN : ZOOM_DOUBLE_TAP, anchor, view);
}

/** Faktor skala untuk roda mouse (ctrl+scroll atau scroll biasa saat sudah diperbesar). */
export function wheelScale(current: number, deltaY: number): number {
  const factor = Math.exp(-deltaY * 0.0015);
  return clampScale(current * factor);
}
