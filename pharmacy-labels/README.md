# Medication Label Studio

`label-studio.html` is a single offline file for editing, printing and exporting the pharmacy's
**High Alert / LASA / Light-sensitive** shelf labels. It replaces the Microsoft Publisher files.

Open it in Chrome or Edge (double-click it). It needs no internet and no install.

- **Edit**: click a label on the left and change the name, vendor, code, banners, batch, expiry, quantity, mark or copies.
- **Print**: tick the labels you want, choose a **Layout** in the top bar, then click **Print selected**.
  Layouts: 6 per A4 page (default, full size with cutting space), 8 per A4 page, 6 per US Letter page,
  or 1 per page for a label printer (102 × 72 mm).
- **Two batches**: set **Batch numbers on this label** to *2 batches*. The label then prints a two-row
  table (Batch No. / Expiry Date / QTY) with a *use first* tick box for each batch.
- **PDF**: click **PDF of selected**, or **PDF of this label**, to download a vector PDF directly.
- **Excel**: **Export CSV** saves the list. Edit it in Excel, save it as CSV, then use **Import CSV**.
- Changes are saved automatically in the browser. Use Export CSV as a backup.

Rebuild after editing `src/`: `python3 build.py`.
The 51 starting labels came from `LASA.pub` (42) and `High_Alert.pub` (9).
