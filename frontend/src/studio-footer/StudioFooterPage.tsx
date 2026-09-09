import { useEffect } from 'react'

import BrandLogo from './BrandLogo'
import FooterBackground from './FooterBackground'
import './studio-footer.css'

const PAGE_TITLE = 'Studio — Footer'
const PAGE_DESCRIPTION = 'Fresh ideas, imagination, and creative collaboration.'

export default function StudioFooterPage() {
  useEffect(() => {
    const previousTitle = document.title
    const previousDescription = document
      .querySelector('meta[name="description"]')
      ?.getAttribute('content')
    const previousIcon = document.querySelector("link[rel='icon']")?.getAttribute('href')

    document.title = PAGE_TITLE

    let descriptionMeta = document.querySelector('meta[name="description"]')
    if (!descriptionMeta) {
      descriptionMeta = document.createElement('meta')
      descriptionMeta.setAttribute('name', 'description')
      document.head.appendChild(descriptionMeta)
    }
    descriptionMeta.setAttribute('content', PAGE_DESCRIPTION)

    let iconLink = document.querySelector("link[rel='icon']") as HTMLLinkElement | null
    if (!iconLink) {
      iconLink = document.createElement('link')
      iconLink.rel = 'icon'
      document.head.appendChild(iconLink)
    }
    iconLink.href = '/logo.svg'

    const previousHtmlLang = document.documentElement.lang
    document.documentElement.lang = 'en'

    const previousBodyCss = document.body.style.cssText
    document.body.style.margin = '0'
    document.body.style.minHeight = '100vh'
    document.body.style.color = '#080909'

    const mobile = window.matchMedia('(max-width: 700px)')
    const syncBodyBackground = () => {
      document.body.style.background = mobile.matches ? '#f0eefa' : '#dfe4f2'
    }
    syncBodyBackground()
    mobile.addEventListener('change', syncBodyBackground)

    return () => {
      mobile.removeEventListener('change', syncBodyBackground)
      document.title = previousTitle
      document.documentElement.lang = previousHtmlLang
      document.body.style.cssText = previousBodyCss
      if (descriptionMeta) {
        if (previousDescription == null) descriptionMeta.remove()
        else descriptionMeta.setAttribute('content', previousDescription)
      }
      if (iconLink) {
        if (previousIcon == null) iconLink.remove()
        else iconLink.href = previousIcon
      }
    }
  }, [])

  return (
    <div className="studio-footer-root">
      <footer className="footer" aria-label="Footer">
        <FooterBackground />
        <div className="jobs">
          <span className="tag">have a fresh idea?</span>
          <span className="headline job-title">
            imagination
            <br />
            meets craft
          </span>
          <div className="footer-nav">
            <span>Made</span>
            <span>Story</span>
            <span>In the lab</span>
            <span>Say hey</span>
          </div>
        </div>
        <div className="logo" role="img" aria-label="Studio logo">
          <BrandLogo />
        </div>
        <div className="contact">
          <span className="tag">say hey</span>
          <div className="headline contact-links">
            <span>let’s team up!</span>
            <span>bring us your idea*</span>
          </div>
          <p className="note">*good things start with one spark. let’s make yours.</p>
          <div className="socials">
            <span aria-label="LinkedIn">
              <img src="/linkedin.svg" alt="" width="35" height="35" />
            </span>
            <span aria-label="Instagram">
              <img src="/instagram.svg" alt="" width="35" height="35" />
            </span>
            <span aria-label="TikTok">
              <img src="/tiktok.svg" alt="" width="35" height="35" />
            </span>
          </div>
        </div>
      </footer>
    </div>
  )
}
