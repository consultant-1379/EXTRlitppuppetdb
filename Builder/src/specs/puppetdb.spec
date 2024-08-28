%define debug_package %{nil}

%global realname puppetdb
%global realversion 2.3.8
%global rpmversion <rpm.version>
%global packager <ericsson.rstate>
%global puppetminversion 3.5.1
%global facterminversion 1.7.0
%global monitor %{realname}_monitor

%define __jar_repack 0

%global open_jdk          java-1.7.0-openjdk
%global oracle_jre        EXTRserverjre_CXP9035480
%global puppet_libdir   %(ruby -rrbconfig -e 'puts RbConfig::CONFIG["vendorlibdir"]')
%global puppet_4_libdir   /opt/puppetlabs/puppet/lib/ruby/vendor_ruby
%if 0%{?fedora} >= 18 || 0%{?rhel} >= 7
%global _with_systemd 1
%else
%global _with_systemd 0
%endif

# These macros are not always defined on much older rpm-based systems
%global  _sharedstatedir /var/lib
%global  _realsysconfdir /etc
%global  _initddir       %{_realsysconfdir}/sysconfig
%global  _rundir         /var/run

Name:          EXTRlitppuppetdb_CXP9032594
Version:       %{rpmversion}
Packager:      %{packager}
Release:       1
BuildRoot:     %{_tmppath}/%{realname}-%{version}-%{release}-root-%(%{__id_u} -n)
Summary:       Puppet Centralized Storage Daemon
License:       ASL 2.0

URL:           http://github.com/puppetlabs/puppetdb
Source0:       http://downloads.puppetlabs.com/puppetdb/%{realname}-%{realversion}.tar.gz
Group:         System Environment/Daemons

# jenkins has facter version 1.6.18 that happens to work by chance. See :
# git clone https://github.com/puppetlabs/puppetdb.git
# git show 0549dd5b
# BuildRequires: facter >= %{facterminversion}
# BuildRequires: puppet >= %{puppetminversion}
# Rake is installed on jenkins but not as an RPM so this build
# requirement is satisfied in that environment though not resolved
# BuildRequires: rubygem-rake
BuildRequires: ruby
Requires:      puppet >= %{puppetminversion}
BuildArch:     noarch
BuildRequires: /usr/sbin/useradd
# Required for %%post and %%preun
Requires:       chkconfig
BuildRequires: java >= 1.7.0
Requires:      %{oracle_jre}

%description
Puppetdb %{realversion} repackaged by Ericsson from Puppetlabs source code

%package -n EXTRlitppuppetdbterminus_CXP9032595
Summary: Puppet terminus files to connect to PuppetDB
Group: Development/Libraries
Requires: puppet >= %{puppetminversion}

%description -n EXTRlitppuppetdbterminus_CXP9032595
Puppet-terminus %{realversion} repackaged by Ericsson from Puppetlabs source code

%prep
%setup -q -n %{realname}-%{realversion}
patch -p0 < ../../src/patches/puppetdb-default.diff
patch -p0 < ../../src/patches/puppetdb.default.systemd.diff
patch -p0 < ../../src/patches/puppetdb.service.diff
patch -p0 < ../../src/patches/config-ini.diff

echo 'Unsetting SGID on the tarball directory tree'
chmod -Rc g-s .

%build

%install

export PATH="/usr/bin:${PATH}"
type -fp ruby

rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/%{_initddir}

export LANG=en_US.UTF-8

rake install PARAMS_FILE= DESTDIR=$RPM_BUILD_ROOT
rake terminus PARAMS_FILE= DESTDIR=$RPM_BUILD_ROOT

mkdir -p $RPM_BUILD_ROOT/%{_localstatedir}/log/%{realname}
mkdir -p $RPM_BUILD_ROOT/%{_rundir}/%{realname}
mkdir -p $RPM_BUILD_ROOT/%{_libexecdir}/%{realname}
touch  $RPM_BUILD_ROOT/%{_localstatedir}/log/%{realname}/%{realname}.log

# Copy puppetdb monitor script
mkdir -p $RPM_BUILD_ROOT/usr/share/%{realname}/scripts
install -m 0755 ext/%{monitor}.sh $RPM_BUILD_ROOT/%{_datadir}/%{realname}/scripts/%{monitor}.sh

# Copy monitor service file for RHEL7, monitor init script for RHEL6
%if 0%{?_with_systemd}
install -m 0644 ext/redhat/%{monitor}.service $RPM_BUILD_ROOT/%{_unitdir}/%{monitor}.service
%else
install -m 0755 ext/redhat/%{monitor}_init $RPM_BUILD_ROOT/%{_initddir}/%{monitor}
%endif

%if 0%{?fedora} >= 16 || 0%{?rhel} >= 7 || 0%{?sles_version} >= 12
sed -i '/notifempty/a\    su puppetdb puppetdb' $RPM_BUILD_ROOT/%{_sysconfdir}/logrotate.d/%{realname}
%endif

sed -i '/weekly/a\    maxsize 100M' $RPM_BUILD_ROOT/%{_sysconfdir}/logrotate.d/%{realname}

echo 'Unsetting SGID on the RPMROOT directory tree'
chmod -Rc g-s $RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%pre
# Here we'll do a little bit of cleanup just in case something went horribly
# awry during a previous install/uninstall:
if [ -f "/usr/share/puppetdb/start_service_after_upgrade" ] ; then
   rm /usr/share/puppetdb/start_service_after_upgrade
fi
# If this is an upgrade (as opposed to an install) then we need to check
#  and see if the service is running.  If it is, we need to stop it.
#  we want to shut down and disable the service.
if [ "$1" = "2" ] ; then
%if 0%{?_with_systemd}
    # We test to see if the systemd service file exists because in upgrades from < 1.6.0,
    # puppetdb may still be using sysv and in that case we need to use the sysv tools.
    if [ -f %{_unitdir}/%{realname}.service ]; then
      if /usr/bin/systemctl status %{realname}.service > /dev/null; then
        # If we need to restart the service after the upgrade
        #  is finished, we will touch a temp file so that
        #  we can detect that state
        touch /usr/share/puppetdb/start_service_after_upgrade
        /usr/bin/systemctl stop %{realname}.service >/dev/null 2>&1
      fi
      if /usr/bin/systemctl status %{monitor}.service > /dev/null; then
        /usr/bin/systemctl stop %{monitor}.service >/dev/null 2>&1
      fi
    elif [ -f %{_initddir}/%{realname} ]; then
      if /sbin/service %{realname} status > /dev/null ; then
        # If we need to restart the service after the upgrade
        #  is finished, we will touch a temp file so that
        #  we can detect that state
        touch /usr/share/puppetdb/start_service_after_upgrade
        /sbin/service %{realname} stop >/dev/null 2>&1
      fi
    fi
%else
    if /sbin/service %{realname} status > /dev/null ; then
        # If we need to restart the service after the upgrade
        #  is finished, we will touch a temp file so that
        #  we can detect that state
        touch /usr/share/puppetdb/start_service_after_upgrade
        /sbin/service %{realname} stop >/dev/null 2>&1
    fi
%endif
fi
# Add PuppetDB user
getent group %{realname} > /dev/null || groupadd -r %{realname}
getent passwd %{realname} > /dev/null || \
useradd -r -g %{realname} -d /usr/share/puppetdb -s /sbin/nologin \
     -c "PuppetDB daemon"  %{realname}

%post
%if 0%{?_with_systemd}
# Always reload the .service files if using systemd, in case they have changed.
/usr/bin/systemctl daemon-reload
if [ "$1" = "1" ]; then
    /usr/bin/systemctl enable %{realname}.service
    /usr/bin/systemctl enable %{monitor}.service
fi
%else
# If this is an install (as opposed to an upgrade)...
if [ "$1" = "1" ]; then
  # Register the puppetDB service
  /sbin/chkconfig --add %{realname}
  /sbin/chkconfig --add %{monitor}
fi
%endif

/usr/sbin/puppetdb ssl-setup

chmod 755 /etc/puppetdb
chown -R puppetdb:puppetdb /etc/puppetdb/*
chmod -R 640 /etc/puppetdb/*
chmod -R ug+X /etc/puppetdb/*

chgrp puppetdb /var/log/puppetdb
chmod 775 /var/log/puppetdb

chown -R puppetdb:puppetdb /var/lib/puppetdb

if [ "$1" = "2" ] ; then
    if [ -f "/usr/share/puppetdb/start_service_after_upgrade" ] ; then
        rm /usr/share/puppetdb/start_service_after_upgrade
        for svc in %{realname} %{monitor}
        do
            %if 0%{?_with_systemd}
                /usr/bin/systemctl start ${svc}.service >/dev/null 2>&1
            %else
                /sbin/service ${svc} start >/dev/null 2>&1
            %endif
        done
    fi
fi

%if 0%{?_with_systemd}
if [ $1 -ge 1 ] ; then
    /bin/systemctl try-restart %{monitor} >/dev/null 2>&1 || :
fi
%else
if [ "$1" -ge 1 ]; then
  /sbin/service %{monitor} restart &>/dev/null || :
fi
%endif

%preun
# If this is an uninstall (as opposed to an upgrade) then
#  we want to shut down and disable the service.
if [ "$1" = "0" ] ; then
    for svc in %{realname} %{monitor}
    do
        %if 0%{?_with_systemd}
            /usr/bin/systemctl stop ${svc}.service >/dev/null 2>&1
            /usr/bin/systemctl disable ${svc}.service >/dev/null 2>&1
        %else
            /sbin/service ${svc} stop >/dev/null 2>&1
            /sbin/chkconfig --del ${svc}
        %endif
    done
fi

# Package removal
%if 0%{?_with_systemd}
if [ $1 -eq 0 ] ; then
    /bin/systemctl --no-reload disable %{monitor} > /dev/null 2>&1 || :
    /bin/systemctl stop %{monitor} > /dev/null 2>&1 || :
fi
%else
if [ "$1" = 0 ] ; then
  /sbin/service %{monitor} stop > /dev/null 2>&1
  /sbin/chkconfig --del %{monitor}
fi
%endif

%postun
# Remove the rundir if this is an uninstall (as opposed to an upgrade)...
if [ "$1" = "0" ]; then
    rm -rf %{_rundir}/%{realname} || :
    rm -rf %{_rundir}/%{monitor} || :
fi

%files
%defattr(-, root, root)
%doc *.md
%doc documentation
%if 0%{?suse_version}
%dir %{_sysconfdir}/%{realname}
%dir %{_sysconfdir}/%{realname}/conf.d
%endif
%config(noreplace)%{_sysconfdir}/%{realname}/conf.d/config.ini
%config(noreplace)%{_sysconfdir}/%{realname}/logback.xml
%config(noreplace)%{_sysconfdir}/%{realname}/conf.d/database.ini
%config(noreplace)%{_sysconfdir}/%{realname}/conf.d/jetty.ini
%config(noreplace)%{_sysconfdir}/%{realname}/conf.d/repl.ini
%config%{_realsysconfdir}/logrotate.d/%{realname}
%config%{_realsysconfdir}/sysconfig/%{realname}
%if 0%{?_with_systemd}
%{_unitdir}/%{realname}.service
%{_unitdir}/%{monitor}.service
%else
%{_initddir}/%{realname}
%{_initddir}/%{monitor}
%endif
%{_sbindir}/puppetdb-ssl-setup
%{_sbindir}/puppetdb-foreground
%{_sbindir}/puppetdb-import
%{_sbindir}/puppetdb-export
%{_sbindir}/puppetdb-anonymize
%{_sbindir}/puppetdb
%dir %{_libexecdir}/%{realname}
%{_libexecdir}/%{realname}/puppetdb-ssl-setup
%{_libexecdir}/%{realname}/puppetdb-foreground
%{_libexecdir}/%{realname}/puppetdb-import
%{_libexecdir}/%{realname}/puppetdb-export
%{_libexecdir}/%{realname}/puppetdb-anonymize
%{_libexecdir}/%{realname}/%{realname}.env
%{_datadir}/%{realname}
%{_sharedstatedir}/%{realname}
%dir %{_localstatedir}/log/%{realname}
%ghost %{_localstatedir}/log/%{realname}/%{realname}.log
%ghost %{_rundir}/%{realname}

%files -n EXTRlitppuppetdbterminus_CXP9032595
%defattr(-, root, root)
%{puppet_libdir}/puppet/application/storeconfigs.rb
%{puppet_libdir}/puppet/face/node/deactivate.rb
%{puppet_libdir}/puppet/face/node/status.rb
%{puppet_libdir}/puppet/face/storeconfigs.rb
%{puppet_libdir}/puppet/indirector/catalog/puppetdb.rb
%{puppet_libdir}/puppet/indirector/facts/puppetdb.rb
%{puppet_libdir}/puppet/indirector/facts/puppetdb_apply.rb
%{puppet_libdir}/puppet/indirector/node/puppetdb.rb
%{puppet_libdir}/puppet/indirector/resource/puppetdb.rb
%{puppet_libdir}/puppet/reports/puppetdb.rb
%{puppet_libdir}/puppet/util/puppetdb.rb
%{puppet_libdir}/puppet/util/puppetdb/char_encoding.rb
%{puppet_libdir}/puppet/util/puppetdb/command.rb
%{puppet_libdir}/puppet/util/puppetdb/command_names.rb
%{puppet_libdir}/puppet/util/puppetdb/config.rb
%{puppet_libdir}/puppet/util/puppetdb/blacklist.rb
%{puppet_4_libdir}/puppet/application/storeconfigs.rb
%{puppet_4_libdir}/puppet/face/node/deactivate.rb
%{puppet_4_libdir}/puppet/face/node/status.rb
%{puppet_4_libdir}/puppet/face/storeconfigs.rb
%{puppet_4_libdir}/puppet/indirector/catalog/puppetdb.rb
%{puppet_4_libdir}/puppet/indirector/facts/puppetdb.rb
%{puppet_4_libdir}/puppet/indirector/facts/puppetdb_apply.rb
%{puppet_4_libdir}/puppet/indirector/node/puppetdb.rb
%{puppet_4_libdir}/puppet/indirector/resource/puppetdb.rb
%{puppet_4_libdir}/puppet/reports/puppetdb.rb
%{puppet_4_libdir}/puppet/util/puppetdb.rb
%{puppet_4_libdir}/puppet/util/puppetdb/char_encoding.rb
%{puppet_4_libdir}/puppet/util/puppetdb/command.rb
%{puppet_4_libdir}/puppet/util/puppetdb/command_names.rb
%{puppet_4_libdir}/puppet/util/puppetdb/config.rb
%{puppet_4_libdir}/puppet/util/puppetdb/blacklist.rb
