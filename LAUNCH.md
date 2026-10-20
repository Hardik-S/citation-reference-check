# Launch checks

Before publishing a release, build a wheel and source archive, install the
wheel into a clean noneditable Python 3.10 and 3.13 environment, and run the
installed command for success, reference issues, invalid files, and help.
Run the full pytest suite with zero skips in each environment. Verify the
distribution version, console-script location under that environment's
`sysconfig` scripts directory, and the source archive contents.

The repository CI matrix covers Ubuntu and Windows on Python 3.10 and 3.13.
Publication additionally requires checking the actual GitHub source archive
against the exact release tag and confirming the installed package version.
No citation support, correctness, relevance, or answer-quality claim is part
of these checks.
