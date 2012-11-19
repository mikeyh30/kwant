from __future__ import division
import numpy as np
from nose.tools import assert_raises
from numpy.testing import assert_equal, assert_almost_equal
import kwant

n = 5
chain = kwant.lattice.Chain()
square = kwant.lattice.Square()

# Test output sanity: that an error is raised if no output is requested,
# and that solving for a subblock of a scattering matrix is the same as taking
# a subblock of the full scattering matrix.
def test_output(solve):
    np.random.seed(3)
    system = kwant.Builder()
    left_lead = kwant.Builder(kwant.TranslationalSymmetry([(-1,)]))
    right_lead = kwant.Builder(kwant.TranslationalSymmetry([(1,)]))
    for b, site in [(system, chain(0)), (system, chain(1)),
                    (left_lead, chain(0)), (right_lead, chain(0))]:
        h = np.random.rand(n, n) + 1j * np.random.rand(n, n)
        h += h.conjugate().transpose()
        b[site] = h
    for b, hopp in [(system, (chain(0), chain(1))),
                    (left_lead, (chain(0), chain(1))),
                    (right_lead, (chain(0), chain(1)))]:
        b[hopp] = 10 * np.random.rand(n, n) + 1j * np.random.rand(n, n)
    system.attach_lead(left_lead)
    system.attach_lead(right_lead)
    fsys = system.finalized()

    result1 = solve(fsys)
    s, modes1 = result1
    assert s.shape == 2 * (sum(i[2] for i in modes1),)
    s1 = result1.submatrix(1, 0)
    s2, modes2 = solve(fsys, 0, [1], [0])
    assert s2.shape == (modes2[1][2], modes2[0][2])
    assert_almost_equal(s1, s2)
    assert_almost_equal(np.dot(s.conjugate().transpose(), s),
                        np.identity(s.shape[0]))
    assert_raises(ValueError, solve, fsys, 0, [])
    modes = solve(fsys)[1]
    h = fsys.leads[0].slice_hamiltonian()
    t = fsys.leads[0].inter_slice_hopping()
    modes1 = kwant.physics.modes(h, t)
    h = fsys.leads[1].slice_hamiltonian()
    t = fsys.leads[1].inter_slice_hopping()
    modes2 = kwant.physics.modes(h, t)
    assert_almost_equal(modes1[0], modes[0][0])
    assert_almost_equal(modes2[1], modes[1][1])


# Test that a system with one lead has unitary scattering matrix.
def test_one_lead(solve):
    np.random.seed(3)
    system = kwant.Builder()
    lead = kwant.Builder(kwant.TranslationalSymmetry([(-1,)]))
    for b, site in [(system, chain(0)), (system, chain(1)),
                    (system, chain(2)), (lead, chain(0))]:
        h = np.random.rand(n, n) + 1j * np.random.rand(n, n)
        h += h.conjugate().transpose()
        b[site] = h
    for b, hopp in [(system, (chain(0), chain(1))),
                    (system, (chain(1), chain(2))),
                    (lead, (chain(0), chain(1)))]:
        b[hopp] = 10 * np.random.rand(n, n) + 1j * np.random.rand(n, n)
    system.attach_lead(lead)
    fsys = system.finalized()

    s = solve(fsys)[0]
    assert_almost_equal(np.dot(s.conjugate().transpose(), s),
                        np.identity(s.shape[0]))


# Test that a system with one lead with no propagating modes has a
# 0x0 S-matrix.
def test_smatrix_shape(solve):
    system = kwant.Builder()
    lead0 = kwant.Builder(kwant.TranslationalSymmetry([(-1,)]))
    lead1 = kwant.Builder(kwant.TranslationalSymmetry([(1,)]))
    for b, site in [(system, chain(0)), (system, chain(1)),
                    (system, chain(2))]:
        b[site] = 2
    lead0[chain(0)] = lambda site: lead0_val
    lead1[chain(0)] = lambda site: lead1_val

    for b, hopp in [(system, (chain(0), chain(1))),
                    (system, (chain(1), chain(2))),
                    (lead0, (chain(0), chain(1))),
                    (lead1, (chain(0), chain(1)))]:
        b[hopp] = -1
    system.attach_lead(lead0)
    system.attach_lead(lead1)
    fsys = system.finalized()

    lead0_val = 4
    lead1_val = 4
    s = solve(fsys, energy=1.0, out_leads=[1], in_leads=[0])[0]
    assert s.shape == (0, 0)

    lead0_val = 2
    lead1_val = 2
    s = solve(fsys, energy=1.0, out_leads=[1], in_leads=[0])[0]
    assert s.shape == (1, 1)

    lead0_val = 4
    lead1_val = 2
    s = solve(fsys, energy=1.0, out_leads=[1], in_leads=[0])[0]
    assert s.shape == (1, 0)

    lead0_val = 2
    lead1_val = 4
    s = solve(fsys, energy=1.0, out_leads=[1], in_leads=[0])[0]
    assert s.shape == (0, 1)

# Test that a translationally invariant system with two leads has only
# transmission and that transmission does not mix modes.
def test_two_equal_leads(solve):
    def check_fsys():
        sol = solve(fsys)
        s, leads = sol[:2]
        assert_almost_equal(np.dot(s.conjugate().transpose(), s),
                            np.identity(s.shape[0]))
        n_modes = leads[0][2]
        assert leads[1][2] == n_modes
        assert_almost_equal(s[: n_modes, : n_modes], 0)
        t_elements = np.sort(abs(np.asarray(s[n_modes :, : n_modes])),
                             axis=None)
        t_el_should_be = n_modes * (n_modes - 1) * [0] + n_modes * [1]
        assert_almost_equal(t_elements, t_el_should_be)
        assert_almost_equal(sol.transmission(1,0), n_modes)
    np.random.seed(11)
    system = kwant.Builder()
    lead = kwant.Builder(kwant.TranslationalSymmetry([(1,)]))
    h = np.random.rand(n, n) + 1j * np.random.rand(n, n)
    h += h.conjugate().transpose()
    h *= 0.8
    t = 4 * np.random.rand(n, n) + 4j * np.random.rand(n, n)
    lead[chain(0)] = system[chain(0)] = h
    lead[chain(0), chain(1)] = t
    system.attach_lead(lead)
    system.attach_lead(lead.reversed())
    fsys = system.finalized()
    check_fsys()

    # Test the same, but with a larger scattering region.
    system = kwant.Builder()
    system[[chain(0), chain(1)]] = h
    system[chain(0), chain(1)] = t
    system.attach_lead(lead)
    system.attach_lead(lead.reversed())
    fsys = system.finalized()
    check_fsys()


# Test a more complicated graph with non-singular hopping.
def test_graph_system(solve):
    np.random.seed(11)
    system = kwant.Builder()
    lead = kwant.Builder(kwant.TranslationalSymmetry([(-1, 0)]))
    lead.default_site_group = system.default_site_group = square

    h = np.random.rand(n, n) + 1j * np.random.rand(n, n)
    h += h.conjugate().transpose()
    h *= 0.8
    t = 4 * np.random.rand(n, n) + 4j * np.random.rand(n, n)
    t1 = 4 * np.random.rand(n, n) + 4j * np.random.rand(n, n)
    lead[0, 0] = system[[(0, 0), (1, 0)]] = h
    lead[0, 1] = system[[(0, 1), (1, 1)]] = 4 * h
    for builder in [system, lead]:
        builder[(0, 0), (1, 0)] = t
        builder[(0, 1), (1, 0)] = t1
        builder[(0, 1), (1, 1)] = 1.1j * t1
    system.attach_lead(lead)
    system.attach_lead(lead.reversed())
    fsys = system.finalized()

    s, leads = solve(fsys)[: 2]
    assert_almost_equal(np.dot(s.conjugate().transpose(), s),
                        np.identity(s.shape[0]))
    n_modes = leads[0][2]
    assert_equal(leads[1][2], n_modes)
    assert_almost_equal(s[: n_modes, : n_modes], 0)
    t_elements = np.sort(abs(np.asarray(s[n_modes :, : n_modes])),
                         axis=None)
    t_el_should_be = n_modes * (n_modes - 1) * [0] + n_modes * [1]
    assert_almost_equal(t_elements, t_el_should_be)


# Test a system with singular hopping.
def test_singular_graph_system(solve):
    np.random.seed(11)

    system = kwant.Builder()
    lead = kwant.Builder(kwant.TranslationalSymmetry([(-1, 0)]))
    lead.default_site_group = system.default_site_group = square
    h = np.random.rand(n, n) + 1j * np.random.rand(n, n)
    h += h.conjugate().transpose()
    h *= 0.8
    t = 4 * np.random.rand(n, n) + 4j * np.random.rand(n, n)
    t1 = 4 * np.random.rand(n, n) + 4j * np.random.rand(n, n)
    lead[0, 0] = system[[(0, 0), (1, 0)]] = h
    lead[0, 1] = system[[(0, 1), (1, 1)]] = 4 * h
    for builder in [system, lead]:
        builder[(0, 0), (1, 0)] = t
        builder[(0, 1), (1, 0)] = t1
    system.attach_lead(lead)
    system.attach_lead(lead.reversed())
    fsys = system.finalized()

    s, leads = solve(fsys)[: 2]
    assert_almost_equal(np.dot(s.conjugate().transpose(), s),
                        np.identity(s.shape[0]))
    n_modes = leads[0][2]
    assert leads[1][2] == n_modes
    assert_almost_equal(s[: n_modes, : n_modes], 0)
    t_elements = np.sort(abs(np.asarray(s[n_modes :, : n_modes])),
                         axis=None)
    t_el_should_be = n_modes * (n_modes - 1) * [0] + n_modes * [1]
    assert_almost_equal(t_elements, t_el_should_be)


# This test features inside the onslice Hamiltonian a hopping matrix with more
# zero eigenvalues than the lead hopping matrix. The previous version of the
# sparse solver failed here.

def test_tricky_singular_hopping(solve):
    system = kwant.Builder()
    lead = kwant.Builder(kwant.TranslationalSymmetry([(4, 0)]))
    lead.default_site_group = system.default_site_group = square

    interface = []
    for i in xrange(n):
        site = square(-1, i)
        interface.append(site)
        system[site] = 0
        for j in xrange(4):
            lead[j, i] = 0
    for i in xrange(n-1):
        system[(-1, i), (-1, i+1)] = -1
        for j in xrange(4):
            lead[(j, i), (j, i+1)] = -1
    for i in xrange(n):
        for j in xrange(4):
            lead[(j, i), (j+1, i)] = -1
    del lead[(1, 0), (2, 0)]

    system.leads.append(kwant.builder.BuilderLead(lead, interface))
    fsys = system.finalized()

    s = solve(fsys, -1.3)[0]
    assert_almost_equal(np.dot(s.conjugate().transpose(), s),
                        np.identity(s.shape[0]))


# Test equivalence between self-energy and scattering matrix representations.
# Also check that transmission works.

def test_self_energy(solve):
    class LeadWithOnlySelfEnergy(object):
        def __init__(self, lead):
            self.lead = lead

        def self_energy(self, energy):
            return self.lead.self_energy(energy)

    np.random.seed(4)
    system = kwant.Builder()
    left_lead = kwant.Builder(kwant.TranslationalSymmetry([(-1,)]))
    right_lead = kwant.Builder(kwant.TranslationalSymmetry([(1,)]))
    for b, site in [(system, chain(0)), (system, chain(1)),
                 (left_lead, chain(0)), (right_lead, chain(0))]:
        h = np.random.rand(n, n) + 1j * np.random.rand(n, n)
        h += h.conjugate().transpose()
        b[site] = h
    for b, hopp in [(system, (chain(0), chain(1))),
                    (left_lead, (chain(0), chain(1))),
                    (right_lead, (chain(0), chain(1)))]:
        b[hopp] = 10 * np.random.rand(n, n) + 1j * np.random.rand(n, n)
    system.attach_lead(left_lead)
    system.attach_lead(right_lead)
    fsys = system.finalized()

    t = solve(fsys, 0, [1], [0]).data
    eig_should_be = np.linalg.eigvals(t * t.conjugate().transpose())
    n_eig = len(eig_should_be)

    fsys.leads[1] = LeadWithOnlySelfEnergy(fsys.leads[1])
    sol = solve(fsys, 0, [1], [0])
    ttdagnew = sol._a_ttdagger_a_inv(1, 0)
    eig_are = np.linalg.eigvals(ttdagnew)
    t_should_be = np.sum(eig_are)
    assert_almost_equal(eig_are.imag, 0)
    assert_almost_equal(np.sort(eig_are.real)[-n_eig :],
                        np.sort(eig_should_be.real))
    assert_almost_equal(t_should_be, sol.transmission(1, 0))

    fsys.leads[0] = LeadWithOnlySelfEnergy(fsys.leads[0])
    sol = solve(fsys, 0, [1], [0])
    ttdagnew = sol._a_ttdagger_a_inv(1, 0)
    eig_are = np.linalg.eigvals(ttdagnew)
    t_should_be = np.sum(eig_are)
    assert_almost_equal(eig_are.imag, 0)
    assert_almost_equal(np.sort(eig_are.real)[-n_eig :],
                        np.sort(eig_should_be.real))
    assert_almost_equal(t_should_be, sol.transmission(1, 0))

def test_self_energy_reflection(solve):
    class LeadWithOnlySelfEnergy(object):
        def __init__(self, lead):
            self.lead = lead

        def self_energy(self, energy):
            return self.lead.self_energy(energy)

    np.random.seed(4)
    system = kwant.Builder()
    left_lead = kwant.Builder(kwant.TranslationalSymmetry([(-1,)]))
    for b, site in [(system, chain(0)), (system, chain(1)),
                 (left_lead, chain(0))]:
        h = np.random.rand(n, n) + 1j * np.random.rand(n, n)
        h += h.conjugate().transpose()
        b[site] = h
    for b, hopp in [(system, (chain(0), chain(1))),
                    (left_lead, (chain(0), chain(1)))]:
        b[hopp] = 10 * np.random.rand(n, n) + 1j * np.random.rand(n, n)
    system.attach_lead(left_lead)
    fsys = system.finalized()

    t = solve(fsys, 0, [0], [0])

    fsys.leads[0] = LeadWithOnlySelfEnergy(fsys.leads[0])
    sol = solve(fsys, 0, [0], [0])

    assert_almost_equal(sol.transmission(0,0), t.transmission(0,0))

def test_very_singular_leads(solve):
    sys = kwant.Builder()
    gr = kwant.lattice.Chain()
    left_lead = kwant.Builder(kwant.TranslationalSymmetry([(-1,)]))
    right_lead = kwant.Builder(kwant.TranslationalSymmetry([(1,)]))
    sys.default_site_group = gr
    left_lead.default_site_group = right_lead.default_site_group = gr
    sys[(0,)] = left_lead[(0,)] = right_lead[(0,)] = np.identity(2)
    left_lead[(0,), (1,)] = np.zeros((2, 2))
    right_lead[(0,), (1,)] = np.identity(2)
    sys.attach_lead(left_lead)
    sys.attach_lead(right_lead)
    fsys = sys.finalized()
    result = solve(fsys)
    assert [i[2] for i in result[1]] == [0, 2]

def test_ldos(ldos):
    sys = kwant.Builder()
    gr = kwant.lattice.Chain()
    lead = kwant.Builder(kwant.TranslationalSymmetry((gr.vec((1,)),)))
    sys.default_site_group = lead.default_site_group = gr
    sys[(0,)] = sys[(1,)] = lead[(0,)] = 0
    sys[(0,), (1,)] = lead[(0,), (1,)] = 1
    sys.attach_lead(lead)
    sys.attach_lead(lead.reversed())
    fsys = sys.finalized()
    assert_almost_equal(ldos(fsys, 0),
                        np.array([1, 1]) / (2 * np.pi))