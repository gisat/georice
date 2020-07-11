FROM ubuntu:18.04

# docker rm $(docker ps -a -q)
# docker rmi $(docker images -a -q)

RUN apt update \
    && apt install -y git=2.17.1 \
    && apt install -y libpcre2* \ 
    && apt install -y swig=3.0.12 \
    && apt install -y g++ \
    && apt install -y python3 \
    && apt install -y python3-pip \
    && apt install -y cmake-curses-gui \
    && apt update \
    && mkdir /home/georice \
	&& chmod 777 /home/georice
	&& git clone https://github.com/gisat/georice.git

#COPY georice/. /home/georice/modules #
	
#RUN cd /home/georice \
#	&& git clone https://gitlab.orfeo-toolbox.org/orfeotoolbox/otb.git \
#   && mkdir /home/georice/modules/otb/build \
#	&& mkdir /home/georice/modules/otb/Downloads \
#	&& mkdir /home/georice/modules/otb/superbuild_install \
#	&& mkdir /home/georice/modules/otb_modul

#COPY make_otb/* /home/georice/modules/otb/build/

#RUN cd /home/georice/otb/build/ \
#	&& make -j4 \
#	&& export PATH=$PATH:/home/georice/otb/superbuild_install/bin \
#	&& export OTB_APPLICATION_PATH=$OTB_APPLICATION_PATH:/home/georice/otb/superbuild_install/bin \
#	&& mkdir /home/georice/filtering/build \
#	&& cd /home/georice/filtering/build \
#	&& CC=$GCCHOME/usr/bin/gcc CXX=$GCCHOME/usr/bin/g++ \
#	&& make -j4
	

#	CC=$GCCHOME/usr/bin/gcc CXX=$GCCHOME/usr/bin/g++ cmake -C ../build.cmake ..
	




	

