FROM ubuntu:18.04

# docker rm $(docker ps -a -q)
# docker rmi $(docker images -a -q)

RUN apt update \
    && apt install -y git \
    && apt install -y libpcre2* \ 
    && apt install -y swig \
    && apt install -y g++ \
    && apt install -y python3 \
    && apt install -y python3-pip \
    && apt install -y cmake-curses-gui \
    && apt update

RUN git clone https://gisat:GI+hu8iUce+@github.com/gisat/georice.git  /home/georice \
	&& chmod 777 /home/georice \
	&& git clone https://gitlab.orfeo-toolbox.org/orfeotoolbox/otb.git /home/georice/modules/otb

RUN mkdir /home/georice/modules/otb/build \
    && mkdir /home/georice/modules/otb/Downloads \
    && mkdir /home/georice/modules/otb/superbuild_install \
    && cp -r  /home/georice/make/make_otb/. /home/georice/modules/otb/build/

RUN cd /home/georice/modules/otb/build/ \
    && make

ENV PATH=$PATH:/home/georice/modules/otb/superbuild_install/bin
ENV OTB_APPLICATION_PATH=$OTB_APPLICATION_PATH:/home/georice/modules/otb/superbuild_install/lib

RUN cd /home/georice/modules/filtering/build \
    && make

ENV PATH=$PATH:/home/georice/modules/filtering/build/bin
ENV OTB_APPLICATION_PATH=$OTB_APPLICATION_PATH:/home/georice/modules/filtering/build/lib/otb/applications

ENV LANG=C.UTF-8

# RUN apt -y install gdal-bin python3-gdal








	

