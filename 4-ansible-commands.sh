#create roles
#ansible-galaxy init defaults

#change /etc/hosts

#change ansible host in /elastic-ansible-debian/inventory/hosts

#change ansible config in /elastic-ansible-debian/ansible.cfg

#for test:
cd /elastic-ansible-debian
ansible-playbook /elastic-ansible-debian/playbooks/test.yml --extra-vars "ansible_sudo_pass=password"

#for full install:
cd /elastic-ansible-debian
ansible-playbook /elastic-ansible-debian/playbooks/site.yml --extra-vars "ansible_sudo_pass=password"


#for run playbook over single node add --limit nodename