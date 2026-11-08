FROM docker.io/library/golang:1.27.3-bookworm@sha256:025eefc1e8dbe63201734a72aaa0a55d7a077f2d8410432f8ae2f3e939f32871 AS gosu-build
ENV GOTOOLCHAIN=local CGO_ENABLED=0 GOOS=linux GOARCH=amd64
ADD https://codeload.github.com/tianon/gosu/tar.gz/6456aaa0f3c854d199d0f037f068eb97515b7513 /tmp/gosu.tar.gz
RUN echo "33d7537d588ea49458b9509bcf4554bdf5ceacc66da71e5caa1058ea3b689c3b  /tmp/gosu.tar.gz" | sha256sum -c - && mkdir /src && tar -xzf /tmp/gosu.tar.gz --strip-components=1 -C /src
WORKDIR /src
RUN go mod download && go build -trimpath -buildvcs=false -ldflags="-s -w -X main.Version=1.19" -o /gosu . && /gosu --version
FROM docker.io/library/postgres:17.11-bookworm@sha256:73bedc9eaa0121b92b9b26bb52e5141b3f6f37479c7ef913c0160455763ca80a AS postgres
COPY --from=gosu-build --chmod=0755 /gosu /usr/local/bin/gosu
FROM docker.io/library/mysql:8.4.13@sha256:72c368d898861f3b3a07af0e6d690400f44f048799ed46822783d9224cc2c86d AS mysql
RUN rpm -e --test mysql-shell && rpm -e mysql-shell && test -x /usr/bin/mysql && test -x /usr/sbin/mysqld
COPY --from=gosu-build --chmod=0755 /gosu /usr/local/bin/gosu
