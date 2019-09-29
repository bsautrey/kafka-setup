# kafka_install.py
# TODO: capture/pipe all output of these commands somewhere they can be used for debugging. add more confirmation output.
# resources:
# https://www.digitalocean.com/community/tutorials/initial-server-setup-with-ubuntu-18-04
# https://askubuntu.com/questions/94060/run-adduser-non-interactively
# https://www.digitalocean.com/community/tutorials/ufw-essentials-common-firewall-rules-and-commands
# https://askubuntu.com/questions/746413/trying-to-install-java-8-unable-to-locate-package-openjdk-8-jre
# https://www.digitalocean.com/community/tutorials/how-to-install-apache-kafka-on-ubuntu-18-04
# https://security.stackexchange.com/questions/45712/how-secure-is-nopasswd-in-passwordless-sudo-mode
# https://kafka-python.readthedocs.io/en/master/install.html
# https://help.ubuntu.com/lts/serverguide/firewall.html
import sys,os,subprocess,socket
from uuid import uuid4

_,install_command = sys.argv

ip_addresses = []
admin_user = ''


if install_command == 'install_root':

    # add new user=ADMIN_USER and user=kafka
    subprocess.call(['adduser','--disabled-password','--gecos','""',admin_user])
    subprocess.call(['adduser','--disabled-password','--gecos','""','kafka'])

    # grant ADMIN_USER and kafka sudo privileges
    subprocess.call(['usermod','-aG','sudo',admin_user])
    subprocess.call(['usermod','-aG','sudo','kafka'])

    # setup firewall and let applications be managed by name using builtin ufw
    subprocess.call(['ufw','app','list'])
    subprocess.call(['ufw','allow','OpenSSH'])
    subprocess.call(['ufw','--force','enable'])
    subprocess.call(['ufw','status'])

    # setup ssh access for user=ADMIN_USER and user=kafka
    subprocess.call(['rsync --archive --chown='+admin_user+':'+admin_user+' ~/.ssh /home/'+admin_user],shell=True)
    subprocess.call(['rsync --archive --chown=kafka:kafka ~/.ssh /home/kafka'],shell=True)

    # allow user=ADMIN_USER and user=kafka to execute sudo commands without password promt
    fn = '/etc/sudoers'
    f = open(fn,'r')
    s = f.read()
    f.close()
    s = s +'\n'+ admin_user+' ALL=(ALL) NOPASSWD:ALL'
    s = s +'\n'+ 'kafka ALL=(ALL) NOPASSWD:ALL'
    f = open(fn,'w')
    f.write(s)
    f.close()
    
elif install_command == 'install_kafka':
    
    # install openjdk 8
    subprocess.call(['sudo','add-apt-repository','ppa:openjdk-r/ppa','-y'])
    subprocess.call(['sudo','apt-get','update'])
    subprocess.call(['sudo','apt-get','install','openjdk-8-jre','-y'])
    
    # downloads, extract, install
    subprocess.call(['mkdir','/home/kafka/Downloads'])
    subprocess.call(['curl','https://www.apache.org/dist/kafka/2.1.1/kafka_2.11-2.1.1.tgz','-o','/home/kafka/Downloads/kafka.tgz'])
    subprocess.call(['mkdir','/home/kafka/kafka'])
    os.chdir('/home/kafka/kafka')
    subprocess.call(['tar','-xvzf','/home/kafka/Downloads/kafka.tgz','--strip','1'])
    
    # set kafka configs
    fn = '/home/kafka/kafka/config/server.properties'
    f = open(fn,'r')
    s = f.read()
    f.close()
    s = s +'\n'+ 'delete.topic.enable=true'
    f = open(fn,'w')
    f.write(s)
    f.close()
    
    # set zookeeper unit definition
    fn = '/etc/systemd/system/zookeeper.service'
    subprocess.call(['sudo','touch',fn])
    subprocess.call(['sudo','chmod','777',fn])
    unit_definition = "[Unit]\nRequires=network.target remote-fs.target\nAfter=network.target remote-fs.target\n\n[Service]\nType=simple\nUser=kafka\nExecStart=/home/kafka/kafka/bin/zookeeper-server-start.sh /home/kafka/kafka/config/zookeeper.properties\nExecStop=/home/kafka/kafka/bin/zookeeper-server-stop.sh\nRestart=on-abnormal\n\n[Install]\nWantedBy=multi-user.target"
    f = open(fn,'w')
    f.write(unit_definition)
    f.close()
    
    # set kafka unit definition
    fn = '/etc/systemd/system/kafka.service'
    subprocess.call(['sudo','touch',fn])
    subprocess.call(['sudo','chmod','777',fn])
    unit_definition = "[Unit]\nRequires=zookeeper.service\nAfter=zookeeper.service\n\n[Service]\nType=simple\nUser=kafka\nExecStart=/bin/sh -c '/home/kafka/kafka/bin/kafka-server-start.sh /home/kafka/kafka/config/server.properties > /home/kafka/kafka/kafka.log 2>&1'\nExecStop=/home/kafka/kafka/bin/kafka-server-stop.sh\nRestart=on-abnormal\n\n[Install]\nWantedBy=multi-user.target'"
    f = open(fn,'w')
    f.write(unit_definition)
    f.close()
    
    # prepare network for running kafka and zookeeper
    ip_address = socket.gethostbyname(socket.gethostname())
    subprocess.call(['sudo','hostnamectl','set-hostname',ip_address])
    subprocess.call(['sudo','ufw','allow','9092'])
    subprocess.call(['sudo','ufw','allow','2181'])
    
    
    # start kafka and check
    subprocess.call(['sudo','systemctl','start','kafka'])
    subprocess.call(['sudo','journalctl','-u','kafka'])
    
    # enable on boot
    #subprocess.call(['sudo','systemctl','enable','kafka']) DOES NOT WORK.
    
    # install pip3
    subprocess.call(['sudo','apt-get','-y','install','python3-pip'])
    
    # install kafka-python with optionals
    subprocess.call(['sudo','pip3','install','kafka-python'])
    subprocess.call(['sudo','pip3','install','lz4'])
    subprocess.call(['sudo','pip3','install','crc32c'])
    
    # assign unique broker_id and zookeeper connection params
    fn = '/home/kafka/kafka/config/server.properties'
    f = open(fn,'r')
    s = f.read()
    f.close()
    broker_id = int(uuid4())
    s = s.replace('broker.id=0','broker.id='+str(broker_id))
    sources = []
    for ip_address in ip_addresses:
        source = ip_address+':2181'
        sources.append(source)
        
    sources_str = ','.join(sources)
    s = s.replace('zookeeper.connect=localhost:2181','zookeeper.connect='+sources_str)
    f = open(fn,'w')
    f.write(s)
    f.close()
    

    
