# Repository and deployment

This repository contains the source and compact recorded results. Raw public radar scans and generated browser data are downloaded/rebuilt, not committed. The author checkpoint is retrieved on first use and hash-checked; its upstream licence and provenance remain included.

Run python run_upgrade.py, then python build_field_console.py. The site directory can be served on a static host. GitHub Actions performs the same rebuild and uploads the generated dashboard.

Enable GitHub Pages in repository Settings > Pages, selecting GitHub Actions as the build source. The workflow requires this repository setting; no personal token or credential should be committed.

The interface presents final offline estimates and a full-segment map. It does not run new radar jobs in the browser or represent a causal online estimator.
