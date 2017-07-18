pybabel extract -o locale\django.pot .
pybabel update -o locale\ru_RU\LC_MESSAGES\django.po -i locale\django.pot -l ru_RU
