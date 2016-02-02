from userroles.models import set_user_role
from userroles import roles
from django.contrib.auth.models import User

# user = User.objects.all()[0]
set_user_role(user, roles.mturk)
