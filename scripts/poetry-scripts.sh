#! /bin/bash
# adding this because Poetry doesn't plan on adding anything akin to `pipenv run <custom bash script>`,
# or at least that was my takeaway from thread https://github.com/python-poetry/poetry/issues/241

# just the one for now, can easily add more options here
set -x

action=$1

if [ "$action" == "m" ]; then
    module_name=$2
    echo "Running tests on only the file: $module_name..."
    poetry run python -m pytest -sv "tests/test_$module_name.py"
elif [ "$action" == "k" ]; then
    test_func_string=$2
    poetry run python -m pytest -sv -k "$test_func_string"
fi
