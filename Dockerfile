FROM jupyter/minimal-notebook
MAINTAINER Grady Fitzpatrick <grady.fitzpatrick@unimelb.edu.au>

# Note:
# This repo forked from Brendan Rius' Jupyter C Kernel.

USER root

WORKDIR /tmp

COPY ./ jupyter_c_kernel/

# Install jupyter_c_kernel
RUN pip install --no-cache-dir jupyter_c_kernel/
RUN cd jupyter_c_kernel && install_c_kernel --user

# Add nbgrader to python environment.
RUN pip install --no-cache-dir nbgrader
RUN jupyter nbextension install --sys-prefix --py nbgrader --overwrite
RUN jupyter nbextension enable --sys-prefix --py nbgrader
RUN jupyter serverextension enable --sys-prefix --py nbgrader

# To disable the Assignment List extension
#jupyter nbextension disable --sys-prefix assignment_list/main --section=tree
#jupyter serverextension disable --sys-prefix nbgrader.server_extensions.assignment_list

# To disable the Create Assignment extension
#jupyter nbextension disable --sys-prefix create_assignment/main

# To disable the Formgrader extension
#jupyter nbextension disable --sys-prefix formgrader/main --section=tree
#jupyter serverextension disable --sys-prefix nbgrader.server_extensions.formgrader

# To disable the Course List extension
RUN jupyter nbextension disable --sys-prefix course_list/main --section=tree
RUN jupyter serverextension disable --sys-prefix nbgrader.server_extensions.course_list

WORKDIR /home/$NB_USER/

USER $NB_USER
