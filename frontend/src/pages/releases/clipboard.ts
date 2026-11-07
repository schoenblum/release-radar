/**
 * Reads what a spreadsheet or a web table puts on the clipboard: tab-separated cells, one
 * row per line. Excel quotes a cell that holds a tab, a line break or a quotation mark.
 */
export function parseClipboard(text: string): string[][] {
  const rows: string[][] = [[]];
  let cell = "";
  let index = 0;
  const source = text.replace(/\r\n?/g, "\n");
  while (index < source.length) {
    const character = source[index];
    if (character === '"' && cell === "") {
      const closing = closingQuote(source, index);
      if (closing !== -1) {
        cell = source.slice(index + 1, closing).replace(/""/g, '"');
        index = closing + 1;
        continue;
      }
    }
    if (character === "\t") {
      rows[rows.length - 1].push(cell);
      cell = "";
    } else if (character === "\n") {
      rows[rows.length - 1].push(cell);
      cell = "";
      rows.push([]);
    } else {
      cell += character;
    }
    index += 1;
  }
  rows[rows.length - 1].push(cell);
  // The line break after the last row does not make another row.
  if (rows.length > 1 && rows[rows.length - 1].length === 1 && rows[rows.length - 1][0] === "") {
    rows.pop();
  }
  return rows.map((row) => row.map((value) => value.trim()));
}

/** A quotation mark only opens a quoted cell if it closes right before a cell ends. */
function closingQuote(source: string, open: number): number {
  let index = open + 1;
  while (index < source.length) {
    if (source[index] === '"') {
      if (source[index + 1] === '"') {
        index += 2;
        continue;
      }
      const next = source[index + 1];
      return next === undefined || next === "\t" || next === "\n" ? index : -1;
    }
    index += 1;
  }
  return -1;
}

/** A range of cells as a spreadsheet expects to receive it. */
export function toClipboard(rows: string[][]): string {
  return rows
    .map((row) =>
      row
        .map((cell) => (/[\t\n"]/.test(cell) ? `"${cell.replace(/"/g, '""')}"` : cell))
        .join("\t"),
    )
    .join("\n");
}
