#!/bin/bash

if [ "$#" -ne 3 ] ; then
   echo "Script requires 3 arguments to execute:"
   echo -e "\t-path to spec file"
   echo -e "\t-rpm version for POM"
   echo -e "\t-R state for rpm"
   exit 1
else
   spec_path=$1
   rpm_version=$2
   r_state=$3
fi

build_directory=$(pwd)

# Set package version taken from integration pom into puppet.spec file
perl -pi.bak -e "s#\<rpm.version\>#${rpm_version}#" SPEC/${spec_path}
perl -pi.bak -e "s#\<ericsson.rstate\>#${r_state}#" SPEC/${spec_path}
perl -pi.bak -e "s#\<build.directory\>#${build_directory}#" SPEC/${spec_path}


rpmbuild --define "_topdir %(pwd)/" --define "_builddir %{_topdir}" --define "_rpmdir %{_topdir}/RPM" --define "_specdir %{_topdir}/SPEC" --define '_rpmfilename %%{NAME}-%%{VERSION}.%%{ARCH}.rpm' --define "_sourcedir %{_topdir}/SOURCES" --define "_localstatedir /var" --define "dist .el7" --define "rhel 7" -bb SPEC/${spec_path}
find . -iname '*.rpm' -print -exec rpm -qlvp {} \;
