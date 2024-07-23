# Configuration files for reconstruction

## Snakemake files

Make sure snakemake is installed

```
python3.11 -m venv env
source env/bin/activate
python3.11 -m pip install --user snakemake
```

Dry run of snakemake file

```
snakemake all -np --snakefile test/run_B27v1.snake --configfiles=test/job_test.json
```