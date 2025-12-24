import { BentoGrid } from '@/components/demo/bento-grid'
import { HeroSection } from '@/components/demo/hero-section'
import { Toaster } from '@/components/ui/sonner'

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <HeroSection />
      <BentoGrid />
      <Toaster />
    </main>
  )
}
