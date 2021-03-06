import sys
sys.path.append('src')
from functions import *
import numpy as np
from numpy.testing import assert_allclose
from overlaps import *
from integrand_and_rk import *
from cython_files.cython_integrand import *
def inputs(nm = 2):
    n2 = 2.5e-20                                # n2 for silica [m/W]
    # 0.0011666666666666668             # loss [dB/m]
    alphadB = np.array([0 for i in range(nm)])
    gama = 1e-3                                 # w/m
    "-----------------------------General options------------------------------"
    maxerr = 1e-13                # maximum tolerable error per step
    "----------------------------Simulation parameters-------------------------"
    N = 10
    z = 10                     # total distance [m]
    nplot = 10                  # number of plots
    nt = 2**N                     # number of grid points
    #dzstep = z/nplot            # distance per step
    dz_less = 1
    dz = 1         # starting guess value of the step

    lamp1 = 1549
    lamp2 = 1555
    lams = 1550
    lamda_c = 1.5508e-6
    lamda = lamp1*1e-9


    P_p1 = 1
    P_p2 = 1
    P_s = 1e-3
    return  n2, alphadB, gama, maxerr, N, z, nt,\
            lamp1, lamp2, lams, lamda_c, lamda, P_p1, P_p2, P_s, dz_less

def same_noise(nm = 2):
    
    n2, alphadB, gama, maxerr, N, z, nt,\
    lamp1, lamp2, lams, lamda_c, lamda,\
        P_p1, P_p2, P_s, dz_less = inputs(nm)

    int_fwm = sim_parameters(n2, nm, alphadB)
    int_fwm.general_options(maxerr, raman_object, 1, 'on')
    int_fwm.propagation_parameters(N, z, dz_less)
    fv, D_freq = fv_creator(lamp1,lamp2, lams, int_fwm)
    sim_wind = sim_window(fv, lamda, lamda_c, int_fwm)
    noise_obj = Noise(int_fwm, sim_wind)
    return noise_obj

noise_obj = same_noise()


def wave_setup(ram, ss, nm, N_sol=1, cython = True, u = None):
    n2, alphadB, gama, maxerr, N, z, nt,\
        lamp1, lamp2, lams, lamda_c, lamda,\
         P_p1, P_p2, P_s, dz_less = inputs(nm)

    int_fwm = sim_parameters(n2, nm, alphadB)
    int_fwm.general_options(maxerr, raman_object, ss, ram)
    int_fwm.propagation_parameters(N, z, dz_less)
    fv, D_freq = fv_creator(lamp1,lamp2, lams, int_fwm)
    sim_wind = sim_window(fv, lamda, lamda_c, int_fwm)

    loss = Loss(int_fwm, sim_wind, amax=int_fwm.alphadB)
    alpha_func = loss.atten_func_full(sim_wind.fv)
    int_fwm.alphadB = alpha_func
    int_fwm.alpha = int_fwm.alphadB
    dnerr = [0]
    index = 1
    master_index = 0
    a_vec = [2.2e-6]

    M1, M2, Q_large = fibre_overlaps_loader(sim_wind.dt)
    betas = load_disp_paramters(sim_wind.w0)

    Dop = dispersion_operator(betas, int_fwm, sim_wind)

    integrand = Integrand(ram, ss, cython = cython, timing = False)
    dAdzmm = integrand.dAdzmm
    pulse_pos_dict_or = ('after propagation', "pass WDM2",
                         "pass WDM1 on port2 (remove pump)",
                         'add more pump', 'out')


    #M1, M2, Q = Q_matrixes(1, n2, lamda, gama=gama)
    raman = raman_object('on', int_fwm.how)
    raman.raman_load(sim_wind.t, sim_wind.dt, M2)

    hf = raman.hf


    u = np.empty(
        [2, int_fwm.nm, len(sim_wind.t)], dtype='complex128')
    U = np.empty([2,int_fwm.nm,
                  len(sim_wind.t)], dtype='complex128')
    w_tiled = np.tile(sim_wind.w + sim_wind.woffset, (int_fwm.nm, 1))

    u[0,:, :] = noise_obj.noise

    fr = 0.18
    kr = 1 -fr
    for i in range(Q_large.shape[1]):
        Q_large[1,i] = 2 * kr * Q_large[0, i] + kr * Q_large[1, i]
    
    
    woff1 = (D_freq['where'][1]+(int_fwm.nt)//2)*2*pi*sim_wind.df
    u[0,0, :] += (P_p1)**0.5 * np.exp(1j*(woff1)*sim_wind.t)



    woff2 = (D_freq['where'][2]+(int_fwm.nt)//2)*2*pi*sim_wind.df
    u[0,0, :] += (P_s)**0.5 * np.exp(1j*(woff2) *
                                           sim_wind.t)


    woff3 = (D_freq['where'][4]+(int_fwm.nt)//2)*2*pi*sim_wind.df
    u[0,1, :] += (P_p2)**0.5 * np.exp(1j*(woff3) *
                                           sim_wind.t)



    U = fftshift(sim_wind.dt*fft(u), axes = -1)
    
    gam_no_aeff = -1j*int_fwm.n2*2*pi/sim_wind.lamda
    dz,dzstep,maxerr = int_fwm.dz,int_fwm.z,int_fwm.maxerr
    Dop = np.ascontiguousarray(Dop)
    w_tiled = np.ascontiguousarray(w_tiled)
    dt = sim_wind.dt
    tsh = sim_wind.tsh
    u_temp = np.ascontiguousarray(u[0,:,:])
    hf = np.ascontiguousarray(hf)

    return U, u_temp,dz,dzstep,maxerr, M1, M2, Q_large, w_tiled, tsh, dt, hf, Dop,gam_no_aeff

"-----------------------Pulse--------------------------------------------"



def pulse_propagations(ram, ss, nm, N_sol=1, cython = True, u = None):

    U, u_temp,dz,dzstep,maxerr, M1, M2, Q_large, w_tiled, tsh, dt, hf, Dop,gam_no_aeff = \
        wave_setup(ram, ss, nm, N_sol=N_sol, cython = cython, u = u)
    U_t, dz = pulse_propagation(u_temp,dz,dzstep,maxerr, M1, M2, Q_large, w_tiled, tsh, hf, Dop,gam_no_aeff)
    U[-1,:,:] = U_t
    u = np.fft.ifft(np.fft.ifftshift(U, axes = -1))

    """
    fig1 = plt.figure()
    plt.plot(sim_wind.fv,w2dbm(np.abs(U[0,0,:])**2))
    plt.plot(sim_wind.fv,w2dbm(np.abs(U[0,1,:])**2))
    plt.savefig('1.png')
    plt.close()


    fig2 = plt.figure()
    plt.plot(sim_wind.fv,w2dbm(np.abs(U[1,0,:])**2))
    plt.plot(sim_wind.fv,w2dbm(np.abs(U[1,1,:])**2))
    plt.savefig('2.png')    
    plt.close()
    
    fig3 = plt.figure()
    plt.plot(sim_wind.t,np.abs(u[0,0,:])**2)
    plt.plot(sim_wind.t,np.abs(u[0,1,:])**2)
    plt.savefig('3.png')
    plt.close()


    fig4 = plt.figure()
    plt.plot(sim_wind.t,np.abs(u[1,0,:])**2)
    plt.plot(sim_wind.t,np.abs(u[1,1,:])**2)
    #plt.xlim(-10*T0, 10*T0)
    plt.savefig('4.png')    
    plt.close()

    fig5 = plt.figure()
    plt.plot(fftshift(sim_wind.w),(np.abs(U[1,0,:])**2 - np.abs(U[0,0,:])**2 ))
    plt.plot(fftshift(sim_wind.w),(np.abs(U[1,1,:])**2 - np.abs(U[0,1,:])**2 ))
    plt.savefig('error.png')
    plt.close()
    
    fig6 = plt.figure()
    plt.plot(sim_wind.t,np.abs(u[0,0,:])**2 - np.abs(u[1,0,:])**2)
    plt.plot(sim_wind.t,np.abs(u[0,1,:])**2 - np.abs(u[1,1,:])**2)
    plt.savefig('error2.png')
    plt.close()
    """
    return u, U, maxerr

"--------------------------------------------------------------------------"

    

class Test_pulse_prop_energy(object):

    def __test__(self,u):
        E = []
        for uu in u:
            sums = 0
            for umode in uu:
                print(umode.shape)
                sums += np.linalg.norm(umode)**2
            E.append(sums)
        np.allclose(E[0], E[1])


    def test_energy_r1_ss1_2(self):
        u, U, maxerr = pulse_propagations(
            'on', 1, nm=2, N_sol=np.abs(10*np.random.randn()))
        self.__test__(u)






class Test_cython():
    def test_s1_ram_on(self):
        ss = 1
        ram = 'on'
        U, u_temp,dz,dzstep,maxerr, M1, M2, Q_large, w_tiled, tsh, dt, hf, Dop,gam_no_aeff = \
            wave_setup(ram, ss, 2, N_sol=10*np.random.randn(), cython = True, u = None)

        N1= dAdzmm(u_temp, M1, M2, Q_large, tsh, hf, w_tiled, gam_no_aeff)
        N2 = dAdzmm_ron_s1(u_temp,np.conjugate(u_temp), M1, M2, Q_large, tsh, hf, w_tiled,gam_no_aeff)
        assert_allclose(N1, N2)
    def test_s0_ram_on(self):
        ss = 0
        ram = 'on'

        U, u_temp,dz,dzstep,maxerr, M1, M2, Q_large, w_tiled, tsh, dt, hf, Dop,gam_no_aeff = \
            wave_setup(ram, ss, 2, N_sol=10*np.random.randn(), cython = True, u = None)

        N1= dAdzmm_ron_s0_cython(u_temp, M1, M2, Q_large, tsh, hf, w_tiled, gam_no_aeff)
        N2 = dAdzmm_ron_s0(u_temp,np.conjugate(u_temp), M1, M2, Q_large, tsh, hf, w_tiled,gam_no_aeff)
        assert_allclose(N1, N2)

    def test_s1_ram_off(self):
        ss = 1
        ram = 'off'
        U, u_temp,dz,dzstep,maxerr, M1, M2, Q_large, w_tiled, tsh, dt, hf, Dop,gam_no_aeff = \
            wave_setup(ram, ss, 2, N_sol=10*np.random.randn(), cython = True, u = None)

        N1= dAdzmm_roff_s1_cython(u_temp, M1, M2, Q_large, tsh, hf, w_tiled, gam_no_aeff)
        N2 = dAdzmm_roff_s1(u_temp,np.conjugate(u_temp), M1, M2, Q_large, tsh, hf, w_tiled,gam_no_aeff)
        assert_allclose(N1, N2)
    
    def test_s0_ram_off(self):
        ss = 0
        ram = 'off'
        U, u_temp,dz,dzstep,maxerr, M1, M2, Q_large, w_tiled, tsh, dt, hf, Dop,gam_no_aeff = \
            wave_setup(ram, ss, 2, N_sol=10*np.random.randn(), cython = True, u = None)
        N1= dAdzmm_roff_s0_cython(u_temp, M1, M2, Q_large, tsh, hf, w_tiled, gam_no_aeff)
        N2 = dAdzmm_roff_s0(u_temp,np.conjugate(u_temp), M1, M2, Q_large, tsh, hf, w_tiled,gam_no_aeff)
        assert_allclose(N1, N2)
    
    
def test_half_disp():

    dz = np.random.randn()
    shape1 = 2
    shape2 = 2**12
    u1 = np.random.randn(shape1, shape2) + 1j * np.random.randn(shape1, shape2)
    u1 *= 10
    Dop = np.random.randn(shape1, shape2) + 1j * np.random.randn(shape1, shape2)
    
    u_python = np.fft.ifft(np.exp(Dop*dz/2) * np.fft.fft(u1))
    u_cython = half_disp_step(u1, Dop/2, dz, shape1, shape2)


    assert_allclose(np.asarray(u_cython), u_python)


def test_cython_norm():
    shape1 = 2
    shape2 = 2**12

    A = np.random.randn(shape1, shape2) + 1j * np.random.randn(shape1, shape2)
    cython_norm = np.asarray(norm(A,shape1,shape2))
    python_norm = np.linalg.norm(A,2, axis = -1).max()

    assert_allclose(cython_norm, python_norm)

def test_fftishit():
    shape1 = 2
    shape2 = 2**12
    A = np.random.randn(shape1, shape2) + 1j * np.random.randn(shape1, shape2)

    cython_shift = np.asarray(cyfftshift(A))
    python_shift = np.fft.fftshift(A, axes = -1)
    assert_allclose(cython_shift, python_shift)

def test_fft():
    shape1 = 2
    shape2 = 2**12
    A = np.random.randn(shape1, shape2) + 1j * np.random.randn(shape1, shape2)

    cython_fft = cyfft(A)
    python_fft = np.fft.fft(A)
    assert_allclose(cython_fft, python_fft)

def test_ifft():
    shape1 = 2
    shape2 = 2**12
    A = np.random.randn(shape1, shape2) + 1j * np.random.randn(shape1, shape2)

    cython_fft = cyifft(A)
    python_fft = np.fft.ifft(A)
    assert_allclose(cython_fft, python_fft)


class Test_CK_operators:

    shape1 = 2
    shape2 = 2**12
    u1 = np.random.randn(shape1, shape2) + 1j * np.random.randn(shape1, shape2)
    A1 = np.random.randn(shape1, shape2) + 1j * np.random.randn(shape1, shape2)
    A2 = np.asarray(A2_temp(u1, A1, shape1, shape2))
    
    A3 = np.asarray(A3_temp(u1, A1, A2, shape1,shape2))
    A4 = np.asarray(A4_temp(u1, A1, A2, A3, shape1,shape2))
    A5 = np.asarray(A5_temp(u1, A1, A2, A3, A4, shape1,shape2))
    A6 = np.asarray(A6_temp(u1, A1, A2, A3, A4, A5, shape1,shape2))
    A = np.asarray(A_temp(u1, A1, A3, A4, A6, shape1,shape2))
    Afourth = np.asarray(Afourth_temp(u1, A1, A3, A4, A5, A6, A, shape1,shape2))
    

    def test_A2(self):
        A2_python = self.u1 + (1./5)*self.A1
        assert_allclose(self.A2, A2_python)

    def test_A3(self):
        A3_python = self.u1 + (3./40)*self.A1 + (9./40)*self.A2
        assert_allclose(self.A3, A3_python)

    def test_A4(self):
        A4_python = self.u1 + (3./10)*self.A1 - (9./10)*self.A2 + (6./5)*self.A3
        assert_allclose(self.A4, A4_python)

    def test_A5(self):
        A5_python = self.u1 - (11./54)*self.A1 + (5./2)*self.A2 - (70./27)*self.A3 + (35./27)*self.A4
        assert_allclose(self.A5, A5_python)

    def test_A6(self):
        A6_python = self.u1 + (1631./55296)*self.A1 + (175./512)*self.A2 + (575./13824)*self.A3 +\
                   (44275./110592)*self.A4 + (253./4096)*self.A5
        assert_allclose(self.A6, A6_python)

    def test_A(self):
        A_python = self.u1 + (37./378)*self.A1 + (250./621)*self.A3 + (125./594) * \
                    self.A4 + (512./1771)*self.A6
        assert_allclose(self.A, A_python)

    def test_Afourth(self):
        Afourth_python = self.u1 + (2825./27648)*self.A1 + (18575./48384)*self.A3 + (13525./55296) * \
        self.A4 + (277./14336)*self.A5 + (1./4)*self.A6
        Afourth_python = self.A - Afourth_python
        assert_allclose(self.Afourth, Afourth_python)