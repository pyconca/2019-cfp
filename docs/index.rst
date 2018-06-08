.. Yak-Bak documentation master file, created by
   sphinx-quickstart on Fri Jun  8 13:54:47 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Yak-Bak
=======

Yak-Bak collects submissions for conferences, and allows for public voting
on the submissions. It reflects the understood best practices as implemented
by :ref:`several community-run tech conferences <YakBakUsers>`. If you use
Yak-Bak, `let us know <mailto:yakbak@bigapplepy.org>`_!


Workflow
--------

Yak-Bak has an opinionated workflow that conferences using it are strongly
advised to follow. The call for proposals and program selection process we
advise is divided into three main phases:

1. **Call for Porposals (CfP)** During the CfP, users can sign up and submit
   talks for eventual consideration.

2. **Public Voting** During public voting, both new users and authors can
   sign up to review talks and vote to help your program committe by rating
   all of the submitted talks. Public voting begins after the CfP closes,
   so no talks can be edited during voting. During public voting, voters can
   not see the author or other identifying information, so that their votes
   are not biased by any pre-existing notions about particular speakers,
   companies, or organizations.

3. **Program Selection** After the votes are cast, the program committee
   should select the talks that have been accepted or waitlisted, mark them
   as such in Yak-Bak, and notify the speakers. Accepted and waitlisted
   speakers can confirm, or withdraw. Accepted and waitlisted speakers can
   edit their proposals. (All other users are banned from logging in).

Read more in the :doc:`user-guide`.


Installation & Configuration
----------------------------

Yak-Bak is a standard Python WSGI application. The best way to install
Yak-Bak on your system is with |pip|_::

    $ pip install Yak-Bak

.. |pip| replace:: ``pip``
.. _pip: https://docs.python.org/3/installing/index.html

You will also need a database. Yak-Bak is tested and developed with
`PostgreSQL <https://www.postgresql.org/>`_, but other databases may work as
well. If you are using PostgreSQL, you should further install the `psycopg2
<https://pypi.org/project/psycopg2/>`_ or `psycopg2-binary
<https://pypi.org/project/psycopg2-binary/>`_  packages.

Copy the `sample configuration file
<https://gitlab.com/bigapplepy/yak-bak/blob/master/yakbak.toml-local>`_ to
your system. You will, at minimum, need to change the ``uri`` setting in the
``[db]`` section.

A complete reference to the configuration is in :doc:`config`.

You can run Yak-Bak with any WSGI container. Direct Yak-Bak to your
configuration file by placing its full path in the ``YAKBAK_CONFIG``
environment variable, then start your WSGI container.


.. _YakBakUsers:

Who Uses Yak-Bak?
-----------------

Yak-Bak was created by the organizers of `PyGotham <https://pygotham.org>`_,
and has been used by them since 2019.


All Documentation
=================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   user-guide
   config
