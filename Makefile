USE_PKGBUILD=1
include /usr/local/share/luggage/luggage.make

TITLE=Crypt_Client
PACKAGE_NAME=Crypt_Client
REVERSE_DOMAIN=com.grahamgilbert
PACKAGE_VERSION=0.8.2
PAYLOAD=\
			pack-crypt

build: clean-build
	xcodebuild -configuration Release

clean-build:
	@sudo rm -rf build

pack-crypt: l_usr_local build l_Library_LaunchDaemons
		@sudo mkdir -p ${WORK_D}/usr/local/crypt
		@sudo ${CP} -R "build/release/Crypt.app" ${WORK_D}/usr/local/crypt/"Crypt.app"
		@sudo ${CP} -R "build_resources/delayed_escrow" ${WORK_D}/usr/local/crypt/delayed_escrow
		@sudo ${CP} build_resources/com.grahamgilbert.crypt.needsescrow.plist ${WORK_D}/Library/LaunchDaemons/com.grahamgilbert.crypt.needsescrow.plist
		@sudo chown -R root:wheel ${WORK_D}/usr/local/crypt
		@sudo chmod 755 ${WORK_D}/usr/local/crypt/delayed_escrow
		#@sudo chmod 755 ${WORK_D}/usr/local/crypt/"Crypt.app"
		@sudo chown root:wheel ${WORK_D}/Library/LaunchDaemons/com.grahamgilbert.crypt.needsescrow.plist
		@sudo chmod 644 ${WORK_D}/Library/LaunchDaemons/com.grahamgilbert.crypt.needsescrow.plist
