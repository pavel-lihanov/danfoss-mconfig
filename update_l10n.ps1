pybabel extract -F babel.cfg -o locale\django.pot .
cmd /c 'pybabel 2>&1' update -o locale\ru_RU\LC_MESSAGES\django.po -i locale\django.pot -l ru_RU