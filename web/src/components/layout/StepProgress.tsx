const STEPS = [
  { id: 1, label: "Genres" },
  { id: 2, label: "Movies" },
  { id: 3, label: "Results" },
] as const

export function StepProgress({ currentStep }: { currentStep: number }) {
  return (
    <nav className="stepper" aria-label="Recommendation steps">
      {STEPS.map((step, index) => (
        <div key={step.id} className="stepper-group" style={{ display: "contents" }}>
          <div
            className={`stepper-step${currentStep === step.id ? " active" : ""}${currentStep > step.id ? " done" : ""}`}
            aria-current={currentStep === step.id ? "step" : undefined}
          >
            <span className="stepper-dot">{step.id}</span>
            <span>{step.label}</span>
          </div>
          {index < STEPS.length - 1 && <span className="stepper-connector" aria-hidden="true" />}
        </div>
      ))}
    </nav>
  )
}
