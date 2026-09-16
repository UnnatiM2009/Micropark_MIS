# data folder

Put the filled-in MIS template here with the name **MIS_Data.xlsx**.

The dashboard looks for `data/MIS_Data.xlsx` when it starts. If the file is
there, every figure comes from it. If it is not there, the dashboard runs on
generated dummy data so that the screens can still be shown and reviewed.

The sheet names and column headings must match the MIS Data Input Template.
See `app/store.py` for the exact mapping.

Real data files are not committed to the repository. See `.gitignore`.
