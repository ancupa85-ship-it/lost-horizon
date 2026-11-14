// Lost Horizon: De Profundis — núcleo del sigilo (fase 2 del plan de migración).
// Guardia de la base de Tarsis: ronda por puntos, vista con cono, distancia y luz, «?» y «!», alerta y captura.
// Se copia en Source/<Módulo>/Tarsis/ del proyecto de Unreal (ver unreal/README.md).
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "TarsisGuard.generated.h"

class UStaticMeshComponent;
class UTextRenderComponent;
class USkeletalMesh;
class UAnimationAsset;

UENUM(BlueprintType)
enum class ETarsisGuardState : uint8
{
	Patrol     UMETA(DisplayName = "Ronda"),
	Suspicious UMETA(DisplayName = "Mosqueado"),
	Alert      UMETA(DisplayName = "Alerta"),
	Search     UMETA(DisplayName = "Buscando"),
	Return     UMETA(DisplayName = "Volviendo"),
	Down       UMETA(DisplayName = "Derribado")
};

UCLASS()
class ATarsisGuard : public ACharacter
{
	GENERATED_BODY()
	// el director pone a los guardias en su ronda al cargar un punto de control (SetState es privado)
	friend class ATarsisDirector;

public:
	ATarsisGuard();
	virtual void Tick(float DeltaSeconds) override;

	/** Puntos de la ronda en coordenadas del mundo (los pone tools/unreal/guardias.py). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Ronda", meta = (MakeEditWidget = "true"))
	TArray<FVector> PatrolPoints;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Ronda")
	float WaitAtPoint = 2.0f;

	/** Espera en cada punto (s), si se quiere distinta por punto; donde falte se usa WaitAtPoint. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Ronda")
	TArray<float> PatrolWaits;

	/** Paso de ronda (cm/s). 175 con las animaciones del maniquí (andar a ~280): zancada natural sin parecer cámara lenta. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Ronda")
	float WalkSpeed = 175.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Ronda")
	float RunSpeed = 430.0f;

	/** Hasta dónde ve con buena luz (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Vista")
	float ViewDistance = 2000.0f;

	/** Medio ángulo del cono de visión (grados). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Vista")
	float ViewHalfAngle = 50.0f;

	/** Más cerca de esto te nota aunque estés a su espalda (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Vista")
	float NearDistance = 220.0f;

	/** Cuánto sube la sospecha por segundo con visibilidad 1 (1 = alerta). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Vista")
	float SuspicionRate = 0.9f;

	/** Cuánto baja por segundo cuando no te ve. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Vista")
	float SuspicionDecay = 0.2f;

	/** Distancia a la que te atrapa en alerta (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Vista")
	float CatchDistance = 130.0f;

	/** Centinela de torre: no anda; barre con la vista (y con su foco) a un lado y a otro y, si te ve, avisa a los de abajo. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torre")
	bool bTowerSentry = false;

	/** Foco de la torre, que gira con el centinela (lo pone tools/unreal/guardias.py). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torre")
	TObjectPtr<AActor> TowerLight;

	/** Hacia dónde mira la torre (yaw en grados) y cuánto barre a cada lado. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torre")
	float TowerYaw = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torre")
	float TowerSweep = 54.0f;

	/** Un compañero (por ejemplo una torre) da la voz: viene corriendo a ese sitio. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void Alarm(const FVector& Where);

	/** Ha oído un ruido (una piedra): se acerca despacio a mirar y busca un rato; luego vuelve a su ronda. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void HearNoise(const FVector& Where);

	/** De tu parte (Ramos, si aceptas llevarlo contigo): no te ve ni da la voz por los cuerpos. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Estado")
	bool bAlly = false;

	/** Deja su ronda y se va a Where, donde se queda (Ramos al portillo de la marisma). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void GoTo(const FVector& Where);

	/** Base en guardia tras una alarma: la sospecha sube más deprisa (lo pone el director). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadWrite, Category = "Tarsis|Estado")
	float AlertBoost = 1.0f;

	/** Dónde cayó derribado (adonde irán a buscarlo por radio si no contesta). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Estado")
	FVector KnockLoc = FVector::ZeroVector;

	/** Segundos que lleva en el suelo. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	float DownTime() const { return State == ETarsisGuardState::Down ? StateT : 0.0f; }

	/** Va a mirar por un ruido (y no por la vista). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	bool IsInvestigating() const { return bInvestigate; }

	/** Se queda quieto Seconds segundos (mientras habla contigo). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void Hold(float Seconds);

	/** Marcado con los prismáticos: el HUD muestra su nombre y estado aunque esté detrás de una pared. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadWrite, Category = "Tarsis|Estado")
	bool bMarked = false;

	/** Derribado por la espalda: cae y duerme KnockOutTime segundos; si otro guardia lo ve, da la alarma. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void KnockOut();

	/** Se le puede derribar ahora desde la posición de Who (cerca, por la espalda, sin ser centinela ni estar ya caído). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	bool CanBeTakenDown(const AActor* Who) const;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis")
	float KnockOutTime = 100.0f;

	/** Nombre para los avisos («Ibarra»...). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis")
	FString GuardName;

	/** Ya lo ha encontrado otro guardia. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Estado")
	bool bFound = false;

	/** Cuerpo con esqueleto (personas del juego web, importadas por tools/unreal/personas.py). Sin él se ve el cilindro provisional. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	TObjectPtr<USkeletalMesh> BodyMesh;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	TObjectPtr<UAnimationAsset> IdleAnim;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	TObjectPtr<UAnimationAsset> WalkAnim;

	/** Mezcla de quieto a andar según la velocidad (BlendSpace1D, lo crea tools/unreal/personas.py). Si está, sustituye a IdleAnim/WalkAnim. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	TObjectPtr<class UBlendSpace> MoveBlend;

	/** Apuntando (en alerta cuando se para). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	TObjectPtr<UAnimationAsset> AimAnim;

	/** Caer al suelo (derribado). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	TObjectPtr<UAnimationAsset> DownAnim;

	/** Velocidad (cm/s) a la que la animación de andar no patina; con más velocidad se reproduce más rápido. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	float WalkAnimSpeed = 150.0f;

	/** Reconstruye los datos de ejecución (segmentos) de una mezcla creada por script. Solo en el editor: Python puede
	 *  rellenar SampleData, pero el motor solo llama a ResampleData desde el editor de mezclas; sin eso la mezcla no
	 *  avanza en el juego y el guardia se desliza con una pose fija. Lo usa tools/unreal/animaciones.py. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Editor")
	static bool RebuildBlendSpace(class UBlendSpace* BlendSpace);

	/** Velocidad (cm/s) de la muestra de trotar en MoveBlend (tools/unreal/animaciones.py); 0 = la mezcla solo llega a andar. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	float RunAnimSpeed = 0.0f;

	/** Giro actual de cabeza y cuello respecto al cuerpo (grados, + a la derecha): mira hacia un ruido, barre al buscar. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Cuerpo")
	float LookYaw = 0.0f;

	/** Pasos que ha dado (pie que apoya, según la animación): para las pruebas y el sonido de sus pasos. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Cuerpo")
	int32 StepsTaken = 0;

	/** Gira en el sitio dando pasos (la animación de andar despacio mientras rota). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Cuerpo")
	bool bTurnStepping = false;

	/** Tiene cuerpo con esqueleto y sus pasos salen de la animación (si no, el director los cuenta por distancia). */
	bool HasFootSync() const { return Pose != nullptr; }

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Estado")
	ETarsisGuardState State = ETarsisGuardState::Patrol;

	/** Sospecha de 0 a 1. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Estado")
	float Meter = 0.0f;

	/** Cuánto ve este guardia al objetivo ahora mismo (0 = nada, 1 = de lleno). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	float Visibility(const AActor* Target) const;

	/** Luz aproximada que recibe un punto (0 = oscuridad, 1 = bien iluminado): farolas, focos e interiores, con sombra. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis", meta = (WorldContext = "WorldContext"))
	static float LightAt(const UObject* WorldContext, FVector Point);

	/** Linterna en la mano (durante el apagón): el cono se ve en la niebla y cuenta como luz para verte. */
	void SetFlashlight(bool bOn);
	bool HasFlashlightOn() const;
	void SetFlashlightShadows(bool bOn);

	/** Arreglando el generador: se queda junto a él barriendo la zona con la linterna (si te ve, deja de arreglar). */
	void StartRepair(const FVector& Center);
	void StopRepair();
	bool IsRepairing() const { return bRepairing; }

	/** Dormido con un dardo: se le puede quitar (E) y vuelve a la pistola. */
	bool bDarted = false;

	/** En alerta porque se lo han mandado por radio (no te ha visto): no abandona por UnseenT antes de llegar. */
	bool bRadioCall = false;

protected:
	virtual void BeginPlay() override;
	virtual void OnConstruction(const FTransform& Transform) override;

	UPROPERTY(VisibleAnywhere, Category = "Tarsis")
	TObjectPtr<UStaticMeshComponent> Body;

	UPROPERTY(VisibleAnywhere, Category = "Tarsis")
	TObjectPtr<UStaticMeshComponent> Head;

	UPROPERTY(VisibleAnywhere, Category = "Tarsis")
	TObjectPtr<UTextRenderComponent> Mark;

	UPROPERTY()
	TObjectPtr<class USpotLightComponent> Flashlight;

	/** Cuerpo que se ve en el juego: copia la pose de la malla animada (oculta) y le añade el giro de cabeza y cuello y
	 *  la inclinación al buscar. Con SingleNode no hay grafo de animación donde meter un LookAt. */
	UPROPERTY()
	TObjectPtr<class UPoseableMeshComponent> Pose;

private:
	void SetupPose();
	void LookTick(float DeltaSeconds);
	void FootTick(float DeltaSeconds);
	float LookTarget = 0.0f;
	float Lean = 0.0f;
	float PrevYaw = 0.0f;
	float YawRate = 0.0f;
	float FootMin[2] = { 0.0f, 0.0f };
	bool bFootUp[2] = { true, true };
	bool bFootInit = false;
	/** Fue a mirar un ruido (para la frase al volver: «habrá sido el viento»). */
	bool bNoiseSearch = false;
	FName HeadBone, NeckBone, SpineBone;
	int32 PointIndex = 0;
	float WaitT = 0.0f;
	float StateT = 0.0f;
	float UnseenT = 0.0f;
	FVector LastSeen = FVector::ZeroVector;
	FVector Home = FVector::ZeroVector;
	FVector MoveDest = FVector(1e9f);
	bool bNoPath = false;
	float DownT = 0.0f;
	bool bInvestigate = false;
	float BlendPos = 0.0f;
	bool bRepairing = false;
	FVector RepairCenter = FVector::ZeroVector;
	float SweepT = 0.0f;
	float RepairLookT = 0.0f;
	float LastRepairNoise = -100.0f;
	FVector RepairLook = FVector::ZeroVector;
	float HoldT = 0.0f;
	void WakeUp();
	void LookForBodies();

	void SetState(ETarsisGuardState NewState);
	void Walk(const FVector& Dest, float Speed);
	void FaceTowards(const FVector& Dest, float DeltaSeconds);
	bool Near2D(const FVector& Dest, float Radius) const;
	void Caught(APawn* Player);
	void UpdateMark();
	void SetupBody();
	void UpdateAnim();
	void TowerTick(float DeltaSeconds, APawn* Player, float V);
	float TowerT = 0.0f;
	float LightPitch = 0.0f;
	TObjectPtr<UAnimationAsset> CurrentAnim;
};
