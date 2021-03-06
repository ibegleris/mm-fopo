import sys
sys.path.append('src')
from functions import *
import os
import pytest
import numpy as np
from numpy.testing import assert_allclose
import overlaps

def test_read_write1():
    #os.system('rm testing_data/hh51_test.hdf5')
    A = np.random.rand(10, 3, 5) + 1j * np.random.rand(10, 3, 5)
    B = np.random.rand(10)
    C = 1
    save_variables('hh51_test', '0', filepath='testing/testing_data/',
                   A=A, B=B, C=C)
    A_copy, B_copy, C_copy = np.copy(A), np.copy(B), np.copy(C)
    del A, B, C
    D = read_variables('hh51_test', '0', filepath='testing/testing_data/')

    A, B, C = D['A'], D['B'], D['C']
    os.system('rm testing/testing_data/hh51_test.hdf5')
    assert_allclose(A, A_copy)


def test_read_write2():

    #os.system('rm testing_data/hh52_test.hdf5')
    A = np.random.rand(10, 3, 5) + 1j * np.random.rand(10, 3, 5)
    B = np.random.rand(10)
    C = 1
    save_variables('hh52_test', '0', filepath='testing/testing_data/',
                   A=A, B=B, C=C)
    A_copy, B_copy, C_copy = np.copy(A), np.copy(B), np.copy(C)
    del A, B, C
    D = read_variables('hh52_test', '0', filepath='testing/testing_data/')
    A, B, C = D['A'], D['B'], D['C']
    # locals().update(D)
    os.system('rm testing/testing_data/hh52_test.hdf5')
    return None


def test_read_write3():

    A = np.random.rand(10, 3, 5) + 1j * np.random.rand(10, 3, 5)
    B = np.random.rand(10)
    C = 1
    save_variables('hh53_test', '0', filepath='testing/testing_data/',
                   A=A, B=B, C=C)
    A_copy, B_copy, C_copy = np.copy(A), np.copy(B), np.copy(C)
    del A, B, C
    D = read_variables('hh53_test', '0', filepath='testing/testing_data/')
    A, B, C = D['A'], D['B'], D['C']
    os.system('rm testing/testing_data/hh53_test.hdf5')
    assert C == C_copy
    return None



def test_dbm2w():
    assert dbm2w(30) == 1


def test1_w2dbm():
    assert w2dbm(1) == 30


def test2_w2dbm():
    a = np.zeros(100)
    floor = np.random.rand(1)[0]
    assert_allclose(w2dbm(a, -floor), -floor*np.ones(len(a)))


def test3_w2dbm():
    with pytest.raises(ZeroDivisionError):
        w2dbm(-1)

def test_load_fibre_param():
    os.system('rm loading_data/M1_M2_new_2m.hdf5')
    M1_,M2_,Q_ = overlaps.fibre_overlaps_loader(1)

    M1, M2,Q = overlaps.fibre_overlaps_loader(1)
    assert_allclose(M1, np.array([[0, 0, 0, 0, 1, 1, 1, 1],
                                     [0, 0, 1, 1, 0, 0, 1, 1],
                                     [0, 1, 0, 1, 0, 1, 0, 1],
                                     [0, 1, 1, 0, 1, 0, 0, 1],
                                     [0, 1, 2, 3, 2, 3, 0, 1]]))

    assert_allclose(M2, np.array([[0, 1, 0, 1], [0, 1, 1, 0]]))
    assert_allclose(M1,M1_)
    assert_allclose(M2, M2_)
    assert_allclose(Q, Q_)