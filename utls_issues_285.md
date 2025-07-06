What is the hash function of the fingerprint in utls? #285
Closed
Closed
What is the hash function of the fingerprint in utls?
#285
@lmmqxyx404
Description
lmmqxyx404
opened on Feb 11, 2024
When I use wireshark, I found that the hash function is md5.

Activity
lmmqxyx404
lmmqxyx404 commented on Feb 11, 2024
lmmqxyx404
on Feb 11, 2024
Author
For example, chrome83 is 9c673fd64a32c8dc.
while in wireshark, it is b32309a26951912be7dba376398abc3b.

gaukas
gaukas commented on Feb 11, 2024
gaukas
on Feb 11, 2024
Contributor
While this question might be more suitable for tlsfingerprint.io or clienthellod, I can answer it here.

TLSFingerprint.io uses a SHA-1 based hash to differentiate TLS fingerprints with great granularity. For what's covered by the hash, please see the original paper: The use of TLS in Censorship Circumvention.

Implementation-wise, you may refer to gaukas/clienthellod and tlsfingerprint.io for implementation in Go and Python/Rust respectively.

As of the hash and long-string representation you saw in wireshark, it is called JA3 (with a new version named JA4?), a TLS fingerprint representation implemented by salesforce. I'm not aware of the original designer of it, but they didn't opt to adapt our design and therefore is of little value to uTLS.

lmmqxyx404
lmmqxyx404 commented on Feb 11, 2024
lmmqxyx404
on Feb 11, 2024
Author
While this question might be more suitable for tlsfingerprint.io or clienthellod, I can answer it here.

TLSFingerprint.io uses a SHA-1 based hash to differentiate TLS fingerprints with great granularity. For what's covered by the hash, please see the original paper: The use of TLS in Censorship Circumvention.

Implementation-wise, you may refer to gaukas/clienthellod and tlsfingerprint.io for implementation in Go and Python/Rust respectively.

As of the hash and long-string representation you saw in wireshark, it is called JA3 (with a new version named JA4?), a TLS fingerprint representation implemented by salesforce. I'm not aware of the original designer of it, but they didn't opt to adapt our design and therefore is of little value to uTLS.

Thanks a lot. I will try sha1 later.


lmmqxyx404
closed this as not plannedon Feb 11, 2024

gaukas
closed this as completedon Feb 11, 2024
lmmqxyx404
lmmqxyx404 commented on Feb 12, 2024
lmmqxyx404
on Feb 12, 2024 · edited by lmmqxyx404
Author
In our study, we collected 3 kinds of information from
the network, including counts and coarse grained times�tamps of unique Client Hello messages, a sample of SNI
and anonymized connection-specific metadata for each unique
Client Hello, and Server Hello responses. We applied for and
received IRB exemption for our collection, and worked with
our institution’s network and IT staff to ensure protection of
user privacy.
Client Hellos For successfully parsed Client Hellos, we
extracted the TLS record version, handshake version, list of
cipher suites, list of supported compression methods, and list
of extensions. When present, we extracted data from several
specific extensions, including the server name indication, el�liptic curves (supported groups), EC point formats, signature
algorithms, and application layer protocol negotiation (ALPN).
We then formed a fingerprint ID from this data, by taking
the SHA1 hash of the TLS record version, handshake version,
cipher suite list, compression method list, extension list, elliptic
curve list, EC point format list, signature algorithm list, and
ALPN list4
. We truncated the SHA1 hash to 64-bits to allow it
to fit a native type in our database. Assuming no adversarially�generated fingerprints, the probability of any collision (given
by the birthday paradox) in a dataset of up to 1,000,000 unique
fingerprints is below 10−7
. For each fingerprint, we recorded
a count of the number of connections it appeared in for each
hour in a PostgreSQL database.
I've read the paper about the SHA1 algorithm, but still haven't found a more accurate description.I wonder if anyone can provide the detailed algorithm used in the site
@gaukas

gaukas
gaukas commented on Feb 12, 2024
gaukas
on Feb 12, 2024 · edited by gaukas
Contributor
Implementation-wise, you may refer to gaukas/clienthellod and tlsfingerprint.io for implementation in Go and Python/Rust respectively.

Please check out the repositories linked from my previous response for the actual implementation. I am pretty sure it has been implemented in multiple programming languages and feel free to pick the one you are more familiar with.

lmmqxyx404
lmmqxyx404 commented on Feb 12, 2024
lmmqxyx404
on Feb 12, 2024
Author
Implementation-wise, you may refer to gaukas/clienthellod and tlsfingerprint.io for implementation in Go and Python/Rust respectively.

Please check out the repositories linked from my previous response for the actual implementation. I am pretty sure it has been implemented in multiple programming languages and feel free to pick the one you are more familiar with.

rust-src/src/tls_parser.rs
I found the file.
And I hate C++...