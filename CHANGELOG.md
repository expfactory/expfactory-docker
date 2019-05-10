# CHANGELOG

This is a manually generated log to track changes to the repository for each release. 
Each section should include general headers such as **Implemented enhancements** 
and **Merged pull requests**. All closed issued and bug fixes should be 
represented.

## [v2.0.0](https://github.com/expfactory/expfactory/releases/tag/v2.0.0) (master)

This is a release candidate.

 - Django version updated to >= 1.11.19
 - auth_views import in apps/users/urls has different import
 - is_authenticated() is no longer a function, boolean is_authenticated
 - python-social-auth way deprecated, removed entirely for now.
 - strings that go into hashlib need to be encoded (utf-8) firsth
 - no programmatic way to install experiments and battery repo, added to run_uwsgi.sh
