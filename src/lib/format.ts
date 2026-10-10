const regionNames = new Intl.DisplayNames(["en"], { type: "region" });

export const countryName = (code: string | null) =>
  code ? (regionNames.of(code) ?? code) : "World";

export const pct = (x: number) => `${(x * 100).toFixed(x < 0.1 ? 1 : 0)}%`;

export const signed = (x: number | null) =>
  x == null ? "–" : `${x > 0 ? "+" : ""}${x.toFixed(2)}`;

export const int = (n: number) => n.toLocaleString("en");
