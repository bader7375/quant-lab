# Medication Label Studio

`label-studio.html` is a single offline file for editing, printing and exporting the pharmacy's
**High Alert / LASA / Light-sensitive** shelf labels. It replaces the Microsoft Publisher files.

Open it in Chrome or Edge (double-click it). It needs no internet and no install.

- **Edit**: click a label on the left and change the name, vendor, code, banners, batch, expiry, quantity, mark or copies.
- **Print**: tick the labels you want, then click **Print selected**. Under **Print settings**, choose the
  label printer (102 × 72 mm), A4 with 8 per page, or US Letter with 6 per page.
- **PDF**: click **PDF of selected**, or **PDF of this label**, to download a vector PDF directly.
- **Excel**: **Export CSV** saves the list. Edit it in Excel, save it as CSV, then use **Import CSV**.
- Changes are saved automatically in the browser. Use Export CSV as a backup.

Rebuild after editing `src/`: `python3 build.py`.
The 51 starting labels came from `LASA.pub` (42) and `High_Alert.pub` (9).
