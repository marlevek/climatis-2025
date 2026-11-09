#!/bin/sh
set -eu
case "${LAB_MODE:-baseline}" in
  baseline|candidate-root|candidate-vhost|merge-baseline|merge-candidate|proxy-naive|proxy-edge|proxy-edge-fixed|precedence-directory|precedence-directory-verified|precedence-vhost) ;;
  *) echo 'Modo de laboratório inválido' >&2; exit 2 ;;
esac
mkdir -p /var/www/lab
cp -R /opt/lab/fixtures/. /var/www/lab/
if [ "${LAB_ROLE:-origin}" = edge ]; then
  cp "/opt/lab/apache/${LAB_MODE}.conf" /etc/apache2/sites-enabled/000-lab.conf
else
  cp "/opt/lab/apache/${LAB_MODE}.conf" /etc/apache2/sites-enabled/000-lab.conf
  case "$LAB_MODE" in
    candidate-root|merge-candidate) cp /opt/lab/rules/candidate-root.htaccess /var/www/lab/.htaccess ;;
    precedence-directory) cp /opt/lab/rules/precedence-directory.htaccess /var/www/lab/.htaccess ;;
    precedence-directory-verified) cp /opt/lab/rules/precedence-directory-verified.htaccess /var/www/lab/.htaccess ;;
    *) cp /opt/lab/rules/baseline.htaccess /var/www/lab/.htaccess ;;
  esac
  case "$LAB_MODE" in
    candidate-root|candidate-vhost|merge-candidate) cp /opt/lab/fixtures/index-candidate.html /var/www/lab/index.html ;;
  esac
  if [ "${LAB_CONTENT_CANONICAL:-0}" = 1 ]; then
    cp /opt/lab/fixtures/index-candidate.html /var/www/lab/index.html
  fi
fi
apache2ctl -t
exec apache2-foreground
