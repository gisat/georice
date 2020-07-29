FROM gisat/otb_modul:sarfiltering

RUN apt update \
    && git clone https://github.com/gisat/georice.git  /home/georice \
	&& chmod 777 /home/georice \
	&& apt -y install gdal-bin python3-gdal

RUN	cd /home/georice/ \
	&& python3 setup.py develop

RUN pip3 install jupyter \
	&& pip3 install ipython

ENV LANG=C.UTF-8

ENV TINI_VERSION v0.6.0

ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /usr/bin/tini

RUN chmod +x /usr/bin/tini

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["jupyter", "notebook", "--port=5000", "--no-browser", "--ip=0.0.0.0", "--allow-root"]






	

