# Docking Pipeline Troubleshooting

This repository accompanies the PyMOL docking helper.  The execution log you pasted shows that
`vina` and `obabel` are invoked from the pipeline, so make sure that both tools are installed and
resolvable from the command line before calling `refresh_wizard` in PyMOL.

## Required command line tools

| Tool | Purpose | Windows installation hints |
|------|---------|-----------------------------|
| [AutoDock Vina](https://vina.scripps.edu/downloads/) | Performs the docking calculations. | Install the pre-built Windows package and add the folder that contains `vina.exe` to your `PATH`.  You can test the installation by opening *Anaconda Prompt* (or PowerShell) and running `where vina`. |
| [Open Babel](https://openbabel.org/docs/Installation/install.html) | Generates and converts ligand/receptor structures. | Use the Windows installer or `conda install -c conda-forge openbabel`.  Afterwards run `obabel -V` to confirm it is discoverable. |

If either command prints “not found”, update the `PATH` environment variable in *System Properties →
Environment Variables* (or configure the conda environment activation script) so that the
executables are visible to the pipeline.

## Input file layout

The pipeline expects the ligand SDF file in the project folder.  When running from
`C:\Users\<user>\Desktop\bcr_abl_flumatinib_docking`, ensure the file is located at
`C:\Users\<user>\Desktop\bcr_abl_flumatinib_docking\SDF\flumatinib.sdf`.
If your ligand file is stored elsewhere, either copy it into the `SDF` directory or adjust the
configuration so that an absolute path is provided.  Forward slashes (`SDF/flumatinib.sdf`) also
work on Windows and avoid escaping issues when the path is parsed by `shlex`.

## Verifying the setup

After installing the dependencies and fixing the input paths, open the `docking` conda environment
and run the following quick checks before launching PyMOL:

```powershell
where vina
obabel -V
python - <<'PY'
from pathlib import Path
for path in [Path('SDF') / 'flumatinib.sdf', Path('outputs')]:
    print(path, 'exists' if path.exists() else 'is missing')
PY
```

These commands confirm that AutoDock Vina and Open Babel are visible on your `PATH`, and that the
ligand/input directories exist prior to starting the docking wizard.  Resolve any missing
prerequisite before re-running the PyMOL workflow.
