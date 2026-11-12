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
	Return     UMETA(DisplayName = "Volviendo")
};

UCLASS()
class ATarsisGuard : public ACharacter
{
	GENERATED_BODY()

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

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Ronda")
	float WalkSpeed = 140.0f;

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

	/** Cuerpo con esqueleto (personas del juego web, importadas por tools/unreal/personas.py). Sin él se ve el cilindro provisional. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	TObjectPtr<USkeletalMesh> BodyMesh;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	TObjectPtr<UAnimationAsset> IdleAnim;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	TObjectPtr<UAnimationAsset> WalkAnim;

	/** Apuntando (en alerta cuando se para). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	TObjectPtr<UAnimationAsset> AimAnim;

	/** Velocidad (cm/s) a la que la animación de andar no patina; con más velocidad se reproduce más rápido. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cuerpo")
	float WalkAnimSpeed = 150.0f;

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

protected:
	virtual void BeginPlay() override;
	virtual void OnConstruction(const FTransform& Transform) override;

	UPROPERTY(VisibleAnywhere, Category = "Tarsis")
	TObjectPtr<UStaticMeshComponent> Body;

	UPROPERTY(VisibleAnywhere, Category = "Tarsis")
	TObjectPtr<UStaticMeshComponent> Head;

	UPROPERTY(VisibleAnywhere, Category = "Tarsis")
	TObjectPtr<UTextRenderComponent> Mark;

private:
	int32 PointIndex = 0;
	float WaitT = 0.0f;
	float StateT = 0.0f;
	float UnseenT = 0.0f;
	FVector LastSeen = FVector::ZeroVector;
	FVector Home = FVector::ZeroVector;
	FVector MoveDest = FVector(1e9f);
	bool bNoPath = false;

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
