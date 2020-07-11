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

RUN git clone https://gisat:GI+hu8iUce+@github.com/gisat/georice.git  /home \
	&& chmod 777 /home/georice \
	&& git clone https://gitlab.orfeo-toolbox.org/orfeotoolbox/otb.git /home/georice/modules \
    && mkdir /home/georice/modules/otb/build \
    && mkdir /home/georice/modules/otb/Downloads \
    && mkdir /home/georice/modules/otb/superbuild_install \
    && copy  /home/georice/make/make_otb/. /home/georice/modules/otb/build/

#RUN cd /home/georice/otb/build/ \
#	&& make -j4 \
#	&& export PATH=$PATH:/home/georice/modules/otb/superbuild_install/bin \
#	&& export OTB_APPLICATION_PATH=$OTB_APPLICATION_PATH:/home/georice/modules/otb/superbuild_install/bin \
#	&& mkdir /home/georice/modules/filtering/build \
#	&& cd /home/georice/modules/filtering/build \
#	&& CC=$GCCHOME/usr/bin/gcc CXX=$GCCHOME/usr/bin/g++ \
#	&& make -j4
	

#	CC=$GCCHOME/usr/bin/gcc CXX=$GCCHOME/usr/bin/g++ cmake -C ../build.cmake ..
	




	

