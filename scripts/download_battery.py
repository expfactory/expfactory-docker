from expfactory.experiment import get_experiments, get_validation_fields
from expfactory.utils import copy_directory, sub_template
from expfactory.vm import custom_battery_download
from glob import glob
import shutil
import json
import os

# Download experiments to temporary directory
tmpdir = custom_battery_download()

static_content = glob("%s/battery/static/*" %tmpdir)

# Update entire static directory
copy_to = os.path.abspath("static/")
for content in static_content:
    basename = os.path.basename(content)
    if os.path.isfile(content):
        shutil.copyfile(content,"%s/%s" %(copy_to,basename))
    else:
        copy_directory(content,"%s/%s" %(copy_to,basename))

shutil.rmtree(tmpdir)
