import { FaLinkedinIn } from 'react-icons/fa'
import { PRODUCT } from '../config/product'
import './UnderConstructionPage.css'

function UnderConstructionPage() {
    return (
        <main className="under-construction" aria-labelledby="under-construction-title">
            <section className="under-construction__content">
                <div className="under-construction__brand" aria-label={PRODUCT.name}>
                    <img
                        className="under-construction__logo"
                        src="/rx-logo.png"
                        alt=""
                        aria-hidden="true"
                    />
                    <span>{PRODUCT.name}</span>
                </div>

                <p className="under-construction__eyebrow">Website update in progress</p>
                <h1 id="under-construction-title">RxChat is under construction</h1>
                <p className="under-construction__message">
                    We are preparing a better experience for you. Follow Fildah on LinkedIn to get the latest updates.
                </p>

                <a
                    className="under-construction__cta"
                    href="https://www.linkedin.com/company/fildah"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    <FaLinkedinIn aria-hidden="true" />
                    Follow Fildah on LinkedIn
                </a>
            </section>
        </main>
    )
}

export default UnderConstructionPage
