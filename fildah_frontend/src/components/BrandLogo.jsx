import { Link } from 'react-router-dom'

export default function BrandLogo() {
  return (
    <Link className="brand-logo" to="/" aria-label="Fildah home">
      <span className="brand-logo__mark" aria-hidden="true">
        F
      </span>
      <span className="brand-logo__text">Fildah</span>
    </Link>
  )
}
