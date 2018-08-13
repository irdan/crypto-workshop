from sage import *

e = 5 # public exponent

while True:
    p = next_prime(ZZ.random_element(2**1024))
    q = next_prime(ZZ.random_element(2**1024))
    n = p * q # order of the finite field
    phi_n = (p-1) * (q-1)

    d = xgcd(e, phi_n)[1]  # private - decryption key

    # workaround for bug, if d is the gcd of phi_n, then it should be positive
    # if it's not, then make it the positive member of the congruence class
    if d < 1:
        d = d + phi_n

    # workaround for a bug, sometimes sage doesn't actually pick prime numbers
    # so throw everything away and try again if this test fails
    if mod(e, phi_n)* d == 1: 
       break

#####################################
# Encryption: mod(plaintext, n)**e  #
# Decryption: mod(ciphertext, n)**d #
#####################################

plaintext1 = 1111111111111111111111111111111111111111111111111111111111111111111111111 # change me if you like
ciphertext1 = mod(plaintext1, n)**e

plaintext2 = 1111111111111111111111111111111111111111111111111111111111111111111111111 # change me if you like
ciphertext2 = mod(plaintext2, n)**e

print(plaintext1 * plaintext2 == mod(ciphertext1 * ciphertext2, n)**d)

print("ciphertexts: {}".format(ciphertext1 * ciphertext2))

print("decrypted multiplied ciphertexts: {}".format(mod(ciphertext1 * ciphertext2, n)**d))
print("plaintexts multiplied: {}".format(plaintext1 * plaintext2))

