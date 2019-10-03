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
RUN pip install --no-cache-dir nbgrader nbgitpuller
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

# Re-enable man pages
RUN sed -i '/path-exclude=\/usr\/share\/man\/*/c\#path-exclude=\/usr\/share\/man\/*' /etc/dpkg/dpkg.cfg.d/excludes

# Install GDB, valgrind and man pages.
RUN apt-get update && apt-get install -y gdb valgrind manpages manpages-dev manpages-posix man less vim

# Install curses, used for an assignment. =)
RUN apt-get update && apt-get install -y libncurses5-dev libncursesw5-dev

RUN /bin/bash jupyter_c_kernel/nbgrader_setup.sh /opt/conda/etc/jupyter/

WORKDIR /home/$NB_USER/

USER $NB_USER
