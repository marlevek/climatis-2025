ARG BASE_IMAGE=php@sha256:884f64b47174de2c0e813270fe7b24a18605729fcebe201302d98c38805530d0
FROM ${BASE_IMAGE}
RUN a2enmod rewrite ssl headers proxy proxy_http \
    && a2dissite 000-default \
    && printf 'Listen 80\nListen 443\n' > /etc/apache2/ports.conf
COPY apache/ /opt/lab/apache/
COPY rules/ /opt/lab/rules/
COPY fixtures/ /opt/lab/fixtures/
COPY php.ini /usr/local/etc/php/conf.d/zz-lab.ini
COPY entrypoint.sh /usr/local/bin/climatis-lab
RUN chmod 755 /usr/local/bin/climatis-lab
ENTRYPOINT ["/usr/local/bin/climatis-lab"]
