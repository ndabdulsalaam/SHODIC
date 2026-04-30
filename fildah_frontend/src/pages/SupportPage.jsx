import { useState } from 'react'
import { FiCheckCircle, FiSend } from 'react-icons/fi'
import { apiRequest } from '../config/api'
import { fallbackProduct } from '../data/fallbacks'
import { useApiResource } from '../hooks/useApiResource'

const initialForm = {
  name: '',
  email: '',
  company: '',
  topic: 'General enquiry',
  product: '',
  message: '',
}

export default function SupportPage() {
  const { data } = useApiResource('/products/', { products: [fallbackProduct] })
  const [form, setForm] = useState(initialForm)
  const [status, setStatus] = useState({ type: '', message: '' })
  const [submitting, setSubmitting] = useState(false)

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function submitForm(event) {
    event.preventDefault()
    setSubmitting(true)
    setStatus({ type: '', message: '' })

    try {
      await apiRequest('/contact/', {
        method: 'POST',
        body: JSON.stringify(form),
      })
      setForm(initialForm)
      setStatus({ type: 'success', message: 'Your message has been sent.' })
    } catch (error) {
      setStatus({ type: 'error', message: error.message })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="page-section">
      <div className="page-hero">
        <p className="eyebrow">Contact</p>
        <h1>Reach the Fildah team.</h1>
        <p>Ask a product question, share a partnership note, or tell us what would help you feel ready to use RxChat.</p>
      </div>

      <form className="support-form" onSubmit={submitForm}>
        <label>
          Name
          <input name="name" value={form.name} onChange={updateField} required />
        </label>
        <label>
          Email
          <input name="email" type="email" value={form.email} onChange={updateField} required />
        </label>
        <label>
          Company
          <input name="company" value={form.company} onChange={updateField} />
        </label>
        <label>
          Topic
          <select name="topic" value={form.topic} onChange={updateField}>
            <option>General enquiry</option>
            <option>Partnership</option>
            <option>Product access</option>
            <option>Support</option>
            <option>Documentation</option>
          </select>
        </label>
        <label>
          Product
          <select name="product" value={form.product} onChange={updateField}>
            <option value="">Fildah</option>
            {(data.products || []).map((product) => (
              <option key={product.slug} value={product.slug}>
                {product.name}
              </option>
            ))}
          </select>
        </label>
        <label className="support-form__message">
          Message
          <textarea name="message" value={form.message} onChange={updateField} rows="7" required />
        </label>
        {status.message && (
          <p className={status.type === 'success' ? 'form-status form-status--success' : 'form-status'}>
            {status.type === 'success' && <FiCheckCircle aria-hidden="true" />}
            {status.message}
          </p>
        )}
        <button className="button button--primary support-form__button" type="submit" disabled={submitting}>
          <FiSend aria-hidden="true" /> {submitting ? 'Sending' : 'Send'}
        </button>
      </form>
    </section>
  )
}
