<!--
  Licensed to the Apache Software Foundation (ASF) under one
  or more contributor license agreements.  See the NOTICE file
  distributed with this work for additional information
  regarding copyright ownership.  The ASF licenses this file
  to you under the Apache License, Version 2.0 (the
  "License"); you may not use this file except in compliance
  with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing,
  software distributed under the License is distributed on an
  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
  KIND, either express or implied.  See the License for the
  specific language governing permissions and limitations
  under the License.
-->

# Apache OpenDAL Go Services Threat Model

## 1. Status

This document defines the security boundary for
`github.com/apache/opendal-go-services`, a companion repository for the Apache
OpenDAL Go binding. The repository packages service-specific prebuilt
native shared libraries, compresses them as embedded `.zst` assets, and
exposes a small Go `Scheme` implementation per service.

The upstream Apache OpenDAL threat model remains authoritative for OpenDAL core,
service implementations, request signing, presigning, the C binding, and the Go
binding FFI API in the packaged upstream OpenDAL revision. This document covers
the additional boundary introduced by this repository: generated Go service
packages, embedded native artifacts, runtime extraction, and their interaction
with custom key signing.

Security reports should follow [`SECURITY.md`](SECURITY.md) and be sent
privately to `private@opendal.apache.org`.

## 2. System Model

Participants in a typical deployment:

| Participant | Role |
| --- | --- |
| Host application | Trusted Go process that imports one or more service modules and supplies `OperatorOptions`. |
| Apache OpenDAL Go binding | Loads the service shared library path returned by `Scheme.Path`, calls the C ABI through FFI, and exposes the Go `Operator` API. |
| This repository's service module | Provides `Scheme.Name`, `Scheme.LoadOnce`, and `Scheme.Path`; decompresses the embedded native library; writes it to a local temporary file. |
| Embedded native artifact | Native code built from upstream Apache OpenDAL with a service-specific feature set. |
| Upstream OpenDAL services and signing code | Construct requests, load credentials when configured, perform request signing and presigning, parse responses, and execute backend operations. |
| Storage backend | Configured storage service, such as S3, GCS, Azure Blob, OSS, Google Drive, Aliyun Drive, local filesystem, or memory. |
| Local operating system | Provides temporary directories, file permissions, dynamic loading, process isolation, and platform libraries. |
| End user of the host application | Outside this repository's direct model. The host application decides whether end-user input may become paths, endpoints, bodies, metadata, or configuration. |
| Network attacker | Usually outside this repository's direct model. Transport policy is owned by upstream OpenDAL, the HTTP client, TLS configuration, and the host environment. |

The high-level flow is:

```text
Go application
  -> opendal-go service Scheme
  -> embedded compressed native artifact
  -> extracted local shared library
  -> Apache OpenDAL Go binding FFI loader
  -> OpenDAL C/Rust service and signing implementation
  -> configured storage backend
```

## 3. Assets

Security-sensitive assets include:

- custom signing keys, access keys, secret keys, session tokens, OAuth tokens,
  refresh tokens, SSH private keys, private key paths, and credential-provider
  state;
- signed requests and presigned URLs;
- object data, object metadata, path names, bucket names, roots, namespaces, and
  endpoints;
- the embedded compressed native artifact in each Go module;
- the decompressed shared library written to a temporary local path;
- generated source code that maps a service name and platform to the intended
  native artifact.

Credential values are secrets. Paths, roots, endpoints, and object names can be
sensitive in some deployments but are not treated as credentials by default.

## 4. Trust Assumptions

This repository assumes:

- the host application is trusted to choose service modules, versions, options,
  endpoints, roots, layers, and credentials;
- the host application performs its own end-user authentication,
  authorization, rate limiting, and input validation before calling OpenDAL;
- the selected storage backend is trusted for backend-side authentication,
  authorization, object bytes, metadata, consistency, and durability;
- the local operating system enforces process and filesystem permissions;
- the distributed Go module and its embedded native artifact have not been
  tampered with before the application imports them.

These assumptions do not remove this repository's responsibility for its own
boundary: it must load the intended artifact, preserve the Go binding contract,
avoid exposing secrets, and avoid making local replacement of executable native
artifacts easier than necessary.

## 5. Security Boundary

The repository's security boundary is the generated Go service package and the
embedded native artifact it distributes.

### 5.1 Native Artifact Loading

Each service package embeds a compressed native shared library and writes it to a
temporary path before the Go binding loads it. This section covers load-path
integrity, not runtime memory integrity. Once native code is loaded into the
process, memory-safety and FFI issues are handled under the upstream OpenDAL and
Go binding security boundary.

In scope:

- another local user can modify or replace the extracted library before it is
  loaded;
- extraction uses predictable, reusable, or unsafe paths that allow replacement,
  symlink, or race attacks;
- `LoadOnce` can report success before the embedded library is fully written and
  ready to load;
- concurrent `LoadOnce` calls can publish an empty, stale, or wrong library
  path;
- `Scheme.Path` can point to a missing, stale, wrong-platform, or
  attacker-created library after `LoadOnce` without host application
  interference;
- decompression or extraction silently produces a partial or corrupted library;
- generated release artifacts bind the wrong native library to a service module.

Out of scope by default:

- runtime memory integrity after the native library is loaded;
- memory corruption bugs inside upstream OpenDAL or the Go binding FFI layer,
  unless this package caused the wrong or unsafe library path to be loaded;
- compromise of the host OS, process, Go module cache, build cache, or package
  mirror;
- a host application intentionally importing or passing the wrong service
  module;
- application code deleting the extracted library after `LoadOnce`;
- application code calling unsupported dynamic-loader APIs directly.

### 5.2 Credential and Custom Signing Key Handling

This repository does not implement request signing itself. Signing is performed
inside upstream OpenDAL native code and related signing libraries. However, this
repository packages that code and participates in the load path that makes it
available to Go applications.

In scope for this repository:

- generated service package code, package metadata, or loading errors that
  print or expose credential-like values available to those packages;
- loading one service artifact when another service was requested, causing
  signing material to be interpreted under the wrong service contract;
- artifact packaging defects that mix incompatible signing implementations with
  a service module.

In scope for upstream OpenDAL, and reportable through the same security process:

- a request signed with credentials from a different `Operator`;
- custom signing keys, secret keys, session tokens, OAuth tokens, or private
  keys leaking through errors, logs, traces, metrics, panic output, or debug
  formatting;
- `disable_config_load`, `disable_ec2_metadata`, `disable_vm_metadata`, or
  similar options failing to disable documented ambient credential sources;
- a signer sending credentials to an endpoint other than the caller-selected
  endpoint;
- presigned URLs with incorrect method, path, expiry, headers, scope, or
  credential identity;
- request signing that silently weakens unrelated transport policy.

Out of scope by default:

- a caller intentionally passing secrets to an attacker-controlled endpoint;
- a host application allowing tenants to choose arbitrary endpoints, roots,
  credentials, regions, buckets, or signing options;
- key generation, storage, rotation, revocation, or HSM/KMS policy outside
  OpenDAL;
- disclosure of signed requests or presigned URLs by the host application after
  OpenDAL returns them.

### 5.3 Backend Operations

This repository does not authorize object operations. It only loads the native
OpenDAL service implementation selected by the host application.

In scope:

- generated package defects that cause operations for one service to be executed
  through a different service implementation;
- packaging a native artifact with missing or unintended service features that
  changes the documented behavior of the module.

Out of scope by default:

- backend IAM, bucket, OAuth, SSH, database, or filesystem policy;
- a backend returning incorrect bytes, metadata, timestamps, ETags, listings, or
  durability claims;
- an application forwarding unauthorized paths, metadata, object bodies, or
  option values into OpenDAL;
- application-level integrity checks, encryption, tenancy, and audit logging.

### 5.4 Local Filesystem Services

For local services such as `fs`, this repository's boundary is still the service
package and native artifact. Path normalization and root confinement belong to
upstream OpenDAL.

Reports should be triaged as upstream OpenDAL issues when they show OpenDAL's
own path construction maps a normalized operation path outside the documented
service root. Reports that depend only on host filesystem permissions, symlink
policy, or caller authorization are usually deployment or application issues
unless upstream OpenDAL documents a stronger guarantee.

### 5.5 Resource Exhaustion

The service packages decompress embedded native artifacts at load time. OpenDAL
operations may also read, write, list, and parse backend data through upstream
native code.

In scope:

- malformed embedded artifacts causing unbounded memory or disk use during
  normal `LoadOnce`;
- generated loading code repeatedly decompressing artifacts despite the
  `LoadOnce` contract;
- decompression or extraction behavior that consumes resources unrelated to the
  embedded artifact size.

Out of scope by default:

- an application reading large objects into memory;
- very large listings returned by a trusted backend;
- missing application-level timeout, throttling, rate limiting, or concurrency
  controls.

## 6. Threats and Expected Controls

| Threat | Expected control |
| --- | --- |
| Wrong service artifact is embedded or loaded | Generation and release checks must bind service name, package name, platform, and artifact path deterministically. |
| Local user replaces extracted shared library | Failure to create a private, non-reusable, non-world-writable extracted library is in scope. |
| Concurrent loading returns inconsistent paths | `LoadOnce` must synchronize initialization and publish a stable successful path. |
| Credential-like data leaks through service package errors | Generated service package errors must not include credential-like values available to those packages. |
| Signing key leaks inside native OpenDAL | Upstream OpenDAL must redact credentials in errors, logging, tracing, metrics, and debug output. |
| Request is signed for the wrong endpoint or service | Upstream OpenDAL signing must bind method, path, query, headers, endpoint, service, region, and credential identity according to the configured backend contract. |
| Operator A credentials sign Operator B requests | Upstream OpenDAL must isolate credential and signer state per operator unless sharing is explicitly configured. |
| Host app lets untrusted users choose endpoints | Host application must authorize configuration input; this is not provided by the service package. |
| Malicious backend returns false data | Application must add end-to-end integrity if it requires cryptographic proof of object bytes. |
| Embedded artifact is tampered with before distribution | Release process should verify provenance, checksums, signatures, and reproducibility appropriate for native artifacts. |

## 7. Triage Dispositions

Use these labels when classifying reports:

| Disposition | Use when |
| --- | --- |
| `VALID` | The report shows a reachable violation of this repository's service package, artifact loading, extraction, or packaging boundary. |
| `VALID-UPSTREAM` | The report affects OpenDAL core, service implementations, C binding, Go binding FFI, or signing behavior packaged here. |
| `VALID-HARDENING` | No clear security-boundary violation exists, but a safer default or clearer documentation would reduce realistic misuse. |
| `OUT-OF-SCOPE: caller-authz` | The report depends on a host application passing unauthorized end-user input to OpenDAL. |
| `OUT-OF-SCOPE: caller-config` | The report depends on the trusted caller choosing a malicious endpoint, root, credential, signing option, or service module. |
| `OUT-OF-SCOPE: trusted-backend` | The report depends on a configured backend lying about bytes, metadata, listings, or authorization. |
| `OUT-OF-SCOPE: host-compromise` | The report requires a compromised process, operating system, package manager, module cache, or filesystem authority beyond this repository's boundary. |
| `OUT-OF-SCOPE: deployment` | The report depends on deployment choices outside the service package, such as shared temporary directories, logging sinks, or missing network controls. |
| `MODEL-GAP` | The report cannot be classified by this model and the model should be revised. |

## 8. In-Scope Examples

- A service module for `s3` embeds or loads an `oss` or `gcs` native artifact.
- `Scheme.LoadOnce` returns success but `Scheme.Path` points to a removed,
  attacker-recreated, or wrong-platform shared library.
- The extracted shared library can be modified by another local user before the
  Go binding loads it.
- Concurrent calls to `LoadOnce` can publish an empty or stale path after a
  failed initialization.
- Generated service package errors include credential-like values available to
  those packages.
- A packaged artifact signs requests with credentials from another operator.
  The root cause may be upstream, but it is security-relevant to users of these
  modules.

## 9. Out-of-Scope Examples

- A web service passes a tenant-controlled path or endpoint into
  `opendal.NewOperator` without authorization.
- A caller intentionally configures an attacker-controlled S3-compatible
  endpoint and the endpoint receives signed requests.
- A cloud bucket policy allows public reads or writes.
- A trusted backend returns misleading ETags, metadata, object bytes, or listing
  order.
- A host application logs a presigned URL after OpenDAL returns it.
- A user with full write access to the application deployment replaces the Go
  module or native artifact before the application starts.

## 10. Revision Triggers

Update this threat model when any of the following changes:

- service packages stop using embedded compressed native artifacts;
- extraction path, file permissions, cleanup, or dynamic loading behavior
  changes;
- new operating systems, CPU architectures, or library formats are added;
- generation starts embedding checksums, signatures, SBOMs, or provenance
  metadata;
- service modules begin handling credentials or signing keys directly in Go;
- upstream OpenDAL changes request signing, presigning, ambient credential
  loading, or credential redaction behavior in ways visible to these modules;
- a vulnerability report is classified as `MODEL-GAP`.

## 11. Maintainer Checklist

Security-sensitive changes should verify:

- generated packages load only their own service artifact;
- embedded artifact names include service, operating system, architecture, and
  library format;
- extracted libraries are private, non-reusable, and non-world-writable;
- `LoadOnce` handles success, failure, and concurrency consistently;
- errors generated by this repository do not contain credentials or custom
  signing material;
- release artifacts can be traced back to the intended upstream Apache OpenDAL
  revision and build configuration;
- documentation remains aligned with upstream Apache OpenDAL security policy and
  threat model.
