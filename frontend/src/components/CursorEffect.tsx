import { useEffect, useRef, useState } from "react"

interface Position {
  x: number
  y: number
}

export default function CursorEffect() {
  const dotRef = useRef<HTMLDivElement>(null)
  const ringRef = useRef<HTMLDivElement>(null)
  const mousePos = useRef<Position>({ x: -100, y: -100 })
  const dotPos = useRef<Position>({ x: -100, y: -100 })
  const ringPos = useRef<Position>({ x: -100, y: -100 })
  const rafId = useRef<number>(0)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    // Hide on touch devices
    if (window.matchMedia("(pointer: coarse)").matches) return

    const handleMouseMove = (e: MouseEvent) => {
      mousePos.current = { x: e.clientX, y: e.clientY }
      if (!visible) setVisible(true)
    }

    const handleMouseLeave = () => {
      mousePos.current = { x: -100, y: -100 }
      dotPos.current = { x: -100, y: -100 }
      ringPos.current = { x: -100, y: -100 }
      setVisible(false)
    }

    window.addEventListener("mousemove", handleMouseMove)
    document.documentElement.addEventListener("mouseleave", handleMouseLeave)

    const animate = () => {
      // Dot: fast follow (lerp factor 0.85 — snappy but smooth)
      dotPos.current.x += (mousePos.current.x - dotPos.current.x) * 0.85
      dotPos.current.y += (mousePos.current.y - dotPos.current.y) * 0.85

      // Ring: slower follow (lerp factor 0.15 — more lag, subtle trail)
      ringPos.current.x += (mousePos.current.x - ringPos.current.x) * 0.15
      ringPos.current.y += (mousePos.current.y - ringPos.current.y) * 0.15

      if (dotRef.current) {
        dotRef.current.style.transform = `translate(${dotPos.current.x}px, ${dotPos.current.y}px)`
      }
      if (ringRef.current) {
        ringRef.current.style.transform = `translate(${ringPos.current.x}px, ${ringPos.current.y}px)`
      }

      rafId.current = requestAnimationFrame(animate)
    }

    rafId.current = requestAnimationFrame(animate)

    return () => {
      window.removeEventListener("mousemove", handleMouseMove)
      document.documentElement.removeEventListener("mouseleave", handleMouseLeave)
      cancelAnimationFrame(rafId.current)
    }
  }, [visible])

  return (
    <>
      {/* Inner dot — small, solid, fast */}
      <div
        ref={dotRef}
        className="cursor-dot"
        aria-hidden="true"
        style={{ opacity: visible ? 1 : 0 }}
      />
      {/* Outer ring — larger, hollow, lagged */}
      <div
        ref={ringRef}
        className="cursor-ring"
        aria-hidden="true"
        style={{ opacity: visible ? 1 : 0 }}
      />
    </>
  )
}
