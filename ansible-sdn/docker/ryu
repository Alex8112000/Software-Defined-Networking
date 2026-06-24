FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y python3 python3-pip vim && pip3 install ryu && pip3 install eventlet==0.30.2
