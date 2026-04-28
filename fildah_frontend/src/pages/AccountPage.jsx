import { useCallback, useEffect, useState } from 'react'
import { FiArrowUpRight, FiLogOut, FiRefreshCw, FiUser } from 'react-icons/fi'
import { NavLink } from 'react-router-dom'
import { apiRequest } from '../config/api'

const emptyAccount = {
  user: null,
  subscription: null,
  organizations: [],
  product_access: [],
  available_products: [],
}

function accountNavClass({ isActive }) {
  return isActive ? 'account-nav__link account-nav__link--active' : 'account-nav__link'
}

function SignInPanel({ onAuthenticated }) {
  const [form, setForm] = useState({ email: '', password: '', otp: '' })
  const [otpRequired, setOtpRequired] = useState(false)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function submit(event) {
    event.preventDefault()
    setLoading(true)
    setMessage('')

    try {
      if (otpRequired) {
        await apiRequest('/auth/verify-device/', {
          method: 'POST',
          body: JSON.stringify({ email: form.email, otp: form.otp }),
        })
        onAuthenticated()
        return
      }

      const payload = await apiRequest('/auth/login/', {
        method: 'POST',
        body: JSON.stringify({ email: form.email, password: form.password }),
      })
      if (payload.otp_required) {
        setOtpRequired(true)
        setMessage(payload.message || 'Verification code sent.')
      } else {
        onAuthenticated()
      }
    } catch (error) {
      setMessage(error.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-panel">
      <FiUser aria-hidden="true" />
      <h2>Sign in to Fildah</h2>
      <p>Use your shared Fildah/RxChat account to view product access and profile details.</p>
      <form onSubmit={submit}>
        <label>
          Email
          <input name="email" type="email" value={form.email} onChange={updateField} required />
        </label>
        {!otpRequired && (
          <label>
            Password
            <input name="password" type="password" value={form.password} onChange={updateField} required />
          </label>
        )}
        {otpRequired && (
          <label>
            Verification code
            <input name="otp" inputMode="numeric" value={form.otp} onChange={updateField} required />
          </label>
        )}
        {message && <p className="form-status">{message}</p>}
        <button className="button button--primary" type="submit" disabled={loading}>
          {loading ? 'Checking' : otpRequired ? 'Verify' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}

function ProductAccessView({ account }) {
  return (
    <div className="account-grid">
      {account.product_access.length ? (
        account.product_access.map((access) => (
          <article className="account-card" key={access.id}>
            <p className="eyebrow">{access.status}</p>
            <h3>{access.product.name}</h3>
            <p>{access.product.short_description || access.product.summary}</p>
            <span>{access.role}</span>
            {access.product.frontend_url && (
              <a className="text-link" href={access.product.frontend_url}>
                Open <FiArrowUpRight aria-hidden="true" />
              </a>
            )}
          </article>
        ))
      ) : (
        <div className="empty-state empty-state--inline">
          <h3>No assigned product access yet.</h3>
          <p>Available Fildah products are listed below for discovery.</p>
        </div>
      )}
      {account.available_products.map((product) => (
        <article className="account-card account-card--muted" key={product.slug}>
          <p className="eyebrow">Available</p>
          <h3>{product.name}</h3>
          <p>{product.short_description || product.summary}</p>
          <a className="text-link" href={product.frontend_url}>
            Open <FiArrowUpRight aria-hidden="true" />
          </a>
        </article>
      ))}
    </div>
  )
}

function ProfileView({ account, onSaved }) {
  const [profile, setProfile] = useState({
    first_name: account.user?.first_name || '',
    last_name: account.user?.last_name || '',
    preferred_name: account.user?.preferred_name || '',
    role: account.user?.role || 'patient',
  })
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setProfile({
      first_name: account.user?.first_name || '',
      last_name: account.user?.last_name || '',
      preferred_name: account.user?.preferred_name || '',
      role: account.user?.role || 'patient',
    })
  }, [account.user])

  function updateField(event) {
    setProfile((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function saveProfile(event) {
    event.preventDefault()
    setSaving(true)
    setMessage('')
    try {
      await apiRequest('/auth/profile/', {
        method: 'PATCH',
        body: JSON.stringify(profile),
      })
      setMessage('Profile updated.')
      onSaved()
    } catch (error) {
      setMessage(error.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="profile-form" onSubmit={saveProfile}>
      <label>
        Preferred name
        <input name="preferred_name" value={profile.preferred_name} onChange={updateField} />
      </label>
      <label>
        First name
        <input name="first_name" value={profile.first_name} onChange={updateField} />
      </label>
      <label>
        Last name
        <input name="last_name" value={profile.last_name} onChange={updateField} />
      </label>
      <label>
        Role
        <select name="role" value={profile.role} onChange={updateField}>
          <option value="patient">Patient</option>
          <option value="pharmacist">Pharmacist</option>
          <option value="physician">Physician</option>
          <option value="nurse">Nurse</option>
          <option value="other_health_professional">Other health professional</option>
        </select>
      </label>
      {message && <p className="form-status">{message}</p>}
      <button className="button button--primary" type="submit" disabled={saving}>
        {saving ? 'Saving' : 'Save profile'}
      </button>
    </form>
  )
}

function OrganizationsView({ account }) {
  if (!account.organizations.length) {
    return <div className="empty-state empty-state--inline"><h3>No organizations yet.</h3><p>Team workspaces will appear here.</p></div>
  }

  return (
    <div className="account-grid">
      {account.organizations.map((organization) => (
        <article className="account-card" key={organization.id}>
          <p className="eyebrow">{organization.role}</p>
          <h3>{organization.name}</h3>
          <p>{organization.plan} plan</p>
        </article>
      ))}
    </div>
  )
}

function BillingView({ account }) {
  return (
    <article className="account-card account-card--wide">
      <p className="eyebrow">Billing</p>
      {account.subscription ? (
        <>
          <h3>{account.subscription.plan.name}</h3>
          <p>Status: {account.subscription.status}</p>
          <strong>{account.subscription.plan.price_monthly}/month</strong>
        </>
      ) : (
        <>
          <h3>No active subscription</h3>
          <p>Billing can start as a shared subscription summary before payment flows are added.</p>
        </>
      )}
    </article>
  )
}

export default function AccountPage({ view = 'overview' }) {
  const [account, setAccount] = useState(emptyAccount)
  const [loading, setLoading] = useState(true)
  const [authenticated, setAuthenticated] = useState(false)
  const [error, setError] = useState('')

  const loadAccount = useCallback(async function loadAccount() {
    setLoading(true)
    setError('')
    try {
      const payload = await apiRequest('/account/products/')
      setAccount(payload)
      setAuthenticated(true)
    } catch (requestError) {
      setAuthenticated(false)
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }, [])

  async function logout() {
    await apiRequest('/auth/logout/', { method: 'POST', body: JSON.stringify({}) })
    setAuthenticated(false)
    setAccount(emptyAccount)
  }

  useEffect(() => {
    loadAccount()
  }, [loadAccount])

  if (!authenticated && !loading) {
    return (
      <section className="page-section account-page">
        <div className="page-hero">
          <p className="eyebrow">Account</p>
          <h1>Shared Fildah account hub.</h1>
          <p>Manage profile, product access, organizations, and billing from the parent brand.</p>
        </div>
        <SignInPanel onAuthenticated={loadAccount} />
        {error && <p className="sr-only">{error}</p>}
      </section>
    )
  }

  return (
    <section className="page-section account-page">
      <div className="page-hero page-hero--account">
        <div>
          <p className="eyebrow">Account</p>
          <h1>{account.user?.preferred_name || account.user?.first_name || 'Fildah account'}</h1>
          <p>{account.user?.email || 'Loading account details.'}</p>
        </div>
        <div className="account-actions">
          <button className="icon-button" type="button" aria-label="Refresh account" onClick={loadAccount}>
            <FiRefreshCw />
          </button>
          <button className="icon-button" type="button" aria-label="Sign out" onClick={logout}>
            <FiLogOut />
          </button>
        </div>
      </div>

      <nav className="account-nav" aria-label="Account navigation">
        <NavLink className={accountNavClass} end to="/account">Overview</NavLink>
        <NavLink className={accountNavClass} to="/account/profile">Profile</NavLink>
        <NavLink className={accountNavClass} to="/account/products">Products</NavLink>
        <NavLink className={accountNavClass} to="/account/organizations">Organizations</NavLink>
        <NavLink className={accountNavClass} to="/account/billing">Billing</NavLink>
      </nav>

      {loading && <div className="empty-state empty-state--inline"><h3>Loading account.</h3><p>Checking your session.</p></div>}
      {!loading && view === 'overview' && (
        <div className="account-grid">
          <article className="account-card">
            <p className="eyebrow">Profile</p>
            <h3>{account.user?.preferred_name || account.user?.first_name || 'User'}</h3>
            <p>{account.user?.role || 'patient'}</p>
          </article>
          <article className="account-card">
            <p className="eyebrow">Products</p>
            <h3>{account.product_access.length}</h3>
            <p>Assigned product access</p>
          </article>
          <article className="account-card">
            <p className="eyebrow">Organizations</p>
            <h3>{account.organizations.length}</h3>
            <p>Team workspaces</p>
          </article>
        </div>
      )}
      {!loading && view === 'profile' && <ProfileView account={account} onSaved={loadAccount} />}
      {!loading && view === 'products' && <ProductAccessView account={account} />}
      {!loading && view === 'organizations' && <OrganizationsView account={account} />}
      {!loading && view === 'billing' && <BillingView account={account} />}
    </section>
  )
}
