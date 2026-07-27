/**
 * Suzuvchi panellar geometriyasi.
 *
 * Xarita butun ekranni egallaydi, chat va statistika esa uning ustida
 * suzib turadi. Panel kengliklari bir joyda saqlanadi, chunki ular ikki
 * marta kerak: panellarni chizishda va xarita "kamerasi"ni ochiq maydon
 * markaziga tekislashda.
 */

export const RAIL_LEFT = 344;
export const RAIL_RIGHT = 384;
/** AI bir hududga chuqur to'xtalganda o'ng panel chatga tomon kengayadi */
export const RAIL_RIGHT_FOCUS = 620;

export function railRight(focus: boolean): number {
  return focus ? RAIL_RIGHT_FOCUS : RAIL_RIGHT;
}

/**
 * Panellar orasidagi ochiq maydon markazi ekran markazidan qancha siljigan.
 * Xarita shu qiymatga teskari surilsa, tanlangan tuman aynan ko'rinadigan
 * bo'shliq o'rtasiga tushadi.
 */
export function stageOffsetX(viewportWidth: number, focus: boolean): number {
  if (viewportWidth === 0) return 0;
  const open = (RAIL_LEFT + (viewportWidth - railRight(focus))) / 2;
  return open - viewportWidth / 2;
}
