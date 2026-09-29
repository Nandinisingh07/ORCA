import { Link, useRouterState } from '@tanstack/react-router'
import { ArrowRight, Bell, Compass, Fish, Map, Menu, MessageCircle, Radio, ShieldAlert, Waves, X, ExternalLink } from 'lucide-react'
import { useState, type ReactNode, type ButtonHTMLAttributes } from 'react'

export const navItems = [
  { to: '/ask', label: 'Ask ORCA', icon: MessageCircle },
  { to: '/conditions', label: 'Ocean conditions', icon: Waves },
  { to: '/fishing-zones', label: 'Fishing zones', icon: Fish },
  { to: '/alerts', label: 'Safety alerts', icon: ShieldAlert },
  { to: '/routes', label: 'Route planning', icon: Compass },
  { to: '/boundaries', label: 'Marine boundaries', icon: Map },
  { to: '/briefings', label: 'Daily briefings', icon: Radio },
] as const

export function Button({ children, variant = 'primary', className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'outline' | 'ghost' | 'light' }) {
  return <button className={`ui-button ui-button-${variant} ${className}`} {...props}>{children}</button>
}

export function Brand({ light = false }: { light?: boolean }) {
  return <Link to="/" className={`brand ${light ? 'brand-light' : ''}`} aria-label="ORCA home"><span className="brand-symbol"><Waves size={27} strokeWidth={2.3} /></span><span className="brand-copy"><strong>ORCA</strong><small>Ocean intelligence platform</small></span></Link>
}

export function SiteShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const pathname = useRouterState({ select: s => s.location.pathname })
  return <>
    <div className="gov-strip"><div className="container strip-inner"><span>Ocean intelligence for India's coasts</span><span className="strip-right">An independent prototype for India's coasts <span className="strip-divider">|</span> <a href="#main-content">Skip to content</a></span></div></div>
    <header className="site-header"><div className="container header-inner"><Brand /><div className="header-meta"><span className="header-meta-dot" /> Designed for safer decisions at sea</div><button className="mobile-menu" aria-label={menuOpen ? 'Close menu' : 'Open menu'} onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X size={23} /> : <Menu size={23} />}</button></div></header>
    <nav className={`main-nav ${menuOpen ? 'nav-open' : ''}`} aria-label="Main navigation"><div className="container nav-inner">{navItems.map(item => <Link key={item.to} to={item.to} onClick={() => setMenuOpen(false)} className={`nav-link ${pathname === item.to ? 'nav-active' : ''}`}>{item.label}</Link>)}</div></nav>
    <main id="main-content">{children}</main>
    <footer className="footer"><div className="container footer-main"><div><Brand light /><p>Bringing ocean information closer to the people who depend on it.</p><span className="footer-note">Independent platform · Not an official Government of India advisory service.</span></div><div className="footer-links"><span>EXPLORE</span><Link to="/ask">Ask ORCA</Link><Link to="/conditions">Ocean conditions</Link><Link to="/alerts">Safety alerts</Link><Link to="/routes">Plan a route</Link></div><div className="footer-links"><span>THE PLATFORM</span><Link to="/about">About ORCA</Link><Link to="/fishing-zones">Fishing zones</Link><Link to="/boundaries">Marine boundaries</Link><Link to="/briefings">Daily briefings</Link></div><div className="footer-links"><span>OFFICIAL SOURCES</span><a href="https://incois.gov.in" target="_blank" rel="noreferrer">INCOIS <ExternalLink size={12}/></a><a href="https://mausam.imd.gov.in" target="_blank" rel="noreferrer">IMD <ExternalLink size={12}/></a><a href="https://bhuvan.nrsc.gov.in" target="_blank" rel="noreferrer">ISRO Bhuvan <ExternalLink size={12}/></a></div></div><div className="container footer-bottom"><span>© 2026 ORCA · Ocean intelligence platform</span><span>Information shown is illustrative and must not be used for navigation or safety decisions.</span></div></footer>
  </>
}

export function SectionHead({ eyebrow, title, description, action, to }: { eyebrow: string; title: string; description?: string; action?: string; to?: string }) { return <div className="section-head"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2>{description && <p>{description}</p>}</div>{action && to && <Link className="text-link" to={to as '/ask'}>{action} <ArrowRight size={17}/></Link>}</div> }

export function StatusPill({ children, tone = 'teal' }: { children: ReactNode; tone?: 'teal' | 'amber' | 'red' }) { return <span className={`status-pill status-${tone}`}><span className="status-dot" />{children}</span> }

export function Notice({ children }: { children: ReactNode }) { return <div className="notice"><Bell size={17}/><span>{children}</span></div> }

export function MiniMap({ variant = 'default' }: { variant?: 'default' | 'route' | 'zones' | 'boundary' }) {
  return <div className={`mini-map map-${variant}`} role="img" aria-label="Illustrative schematic of India's western coast with marine points of interest"><div className="map-grid"/><svg className="map-shape" viewBox="0 0 680 410" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><path d="M0 0H258 Q281 26 250 52 Q237 68 257 89 Q287 110 274 136 Q264 163 295 177 Q312 189 298 215 Q285 235 318 253 Q338 268 330 289 Q315 315 343 337 Q360 362 370 410 H0Z" fill="var(--map-land)"/><path d="M258 0 Q281 26 250 52 Q237 68 257 89 Q287 110 274 136 Q264 163 295 177 Q312 189 298 215 Q285 235 318 253 Q338 268 330 289 Q315 315 343 337 Q360 362 370 410" fill="none" stroke="var(--map-shore)" strokeWidth="3"/><path d="M378 10 Q345 95 402 169 Q430 227 428 294 Q440 354 488 410" fill="none" stroke="var(--map-line)" strokeWidth="2" strokeDasharray="6 7"/></svg><span className="map-label map-land-label">INDIAN COAST</span><span className="map-label map-sea-label">ARABIAN SEA</span><span className="map-place place-one"><i/> Veraval</span><span className="map-place place-two"><i/> Mumbai</span><span className="map-place place-three"><i/> Goa</span>{variant === 'zones' ? <><span className="map-area zone-one"/><span className="map-area zone-two"/></> : variant === 'route' ? <><svg className="route-line" viewBox="0 0 680 410" preserveAspectRatio="none"><path d="M281 125 Q350 140 386 176 T470 209" stroke="var(--map-route)" strokeWidth="4" fill="none" strokeDasharray="8 5"/></svg><span className="map-point point-route">2</span></> : variant === 'boundary' ? <span className="map-boundary-label">Reference boundary</span> : <><span className="map-point point-one">1</span><span className="map-point point-two">2</span></>}<div className="map-caption">ILLUSTRATIVE MAP · NOT FOR NAVIGATION</div></div>
}

export function PageIntro({ eyebrow, title, description, image }: { eyebrow: string; title: string; description: string; image?: string }) { return <div className="page-intro"><div className="container page-intro-inner"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{image && <img src={image} alt="India's coastline and ocean" width={1200} height={800}/>}</div></div> }
