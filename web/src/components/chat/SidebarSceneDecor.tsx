export type SidebarSceneVariant = "lamp" | "console"

type SidebarSceneDecorProps = {
  variant: SidebarSceneVariant
}

const SCENE_ASSETS: Record<SidebarSceneVariant, { src: string; alt: string }> = {
  lamp: {
    src: "/assets/living-room/scene-lamp-left.png",
    alt: "",
  },
  console: {
    src: "/assets/living-room/scene-console-right.png",
    alt: "",
  },
}

export function SidebarSceneDecor({ variant }: SidebarSceneDecorProps) {
  const asset = SCENE_ASSETS[variant]

  return (
    <div
      className={`sidebar-scene-decor sidebar-scene-decor--${variant}`}
      aria-hidden="true"
    >
      <img className="sidebar-scene-decor__art" src={asset.src} alt={asset.alt} />
    </div>
  )
}
