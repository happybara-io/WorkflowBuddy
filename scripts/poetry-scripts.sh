#! /bin/bash
# adding this because Poetry doesn't plan on adding anything akin to `pipenv run <custom bash script>`,
# or at least that was my takeaway from thread https://github.com/python-poetry/poetry/issues/241

# just the one for now, can easily add more options here
set -x

test_file=$1
echo "Running tests on only the file: $test_file..."
poetry run python -m pytest -sv "$test_file"
