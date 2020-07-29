FROM gisat/otb_modul:sarfiltering


RUN git clone https://gisat:GI+hu8iUce+@github.com/gisat/georice.git  /home/georice \
	&& chmod 777 /home/georice



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








	

