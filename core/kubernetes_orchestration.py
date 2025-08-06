"""
Kubernetes deployment configuration and orchestration for TQ GenAI Chat.
Provides container orchestration, auto-scaling, and service mesh integration.
"""

import base64
import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class DeploymentStrategy(Enum):
    """Kubernetes deployment strategies."""

    ROLLING_UPDATE = "RollingUpdate"
    RECREATE = "Recreate"
    BLUE_GREEN = "BlueGreen"
    CANARY = "Canary"


class ServiceType(Enum):
    """Kubernetes service types."""

    CLUSTER_IP = "ClusterIP"
    NODE_PORT = "NodePort"
    LOAD_BALANCER = "LoadBalancer"
    EXTERNAL_NAME = "ExternalName"


@dataclass
class ResourceRequirements:
    """Kubernetes resource requirements."""

    cpu_request: str = "100m"
    cpu_limit: str = "500m"
    memory_request: str = "128Mi"
    memory_limit: str = "512Mi"
    storage_request: str = "1Gi"
    ephemeral_storage_limit: str = "2Gi"


@dataclass
class AutoScalingConfig:
    """Horizontal Pod Autoscaler configuration."""

    min_replicas: int = 1
    max_replicas: int = 10
    target_cpu_utilization: int = 70
    target_memory_utilization: int = 80
    scale_up_stabilization: int = 60  # seconds
    scale_down_stabilization: int = 300  # seconds


@dataclass
class HealthCheckConfig:
    """Health check configuration."""

    readiness_path: str = "/health/ready"
    liveness_path: str = "/health/live"
    startup_path: str = "/health/startup"
    initial_delay: int = 30
    timeout: int = 5
    period: int = 10
    failure_threshold: int = 3
    success_threshold: int = 1


@dataclass
class ServiceConfig:
    """Service configuration."""

    name: str
    image: str
    tag: str = "latest"
    port: int = 8000
    target_port: int = 8000
    replicas: int = 3
    service_type: ServiceType = ServiceType.CLUSTER_IP
    resources: ResourceRequirements = field(default_factory=ResourceRequirements)
    autoscaling: AutoScalingConfig = field(default_factory=AutoScalingConfig)
    health_check: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    environment: dict[str, str] = field(default_factory=dict)
    secrets: dict[str, str] = field(default_factory=dict)
    config_maps: dict[str, str] = field(default_factory=dict)
    volumes: list[dict[str, Any]] = field(default_factory=list)
    ingress: bool = False
    ingress_host: str = ""
    ingress_path: str = "/"
    service_mesh: bool = False

    @property
    def full_image(self) -> str:
        return f"{self.image}:{self.tag}"


class KubernetesManifestGenerator:
    """Generates Kubernetes manifests for TQ GenAI Chat services."""

    def __init__(self, namespace: str = "tq-genai-chat", registry: str = ""):
        self.namespace = namespace
        self.registry = registry
        self.manifests = {}

    def generate_namespace(self) -> dict[str, Any]:
        """Generate namespace manifest."""
        return {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": self.namespace,
                "labels": {
                    "app.kubernetes.io/name": "tq-genai-chat",
                    "app.kubernetes.io/version": "1.0.0",
                },
            },
        }

    def generate_configmap(self, name: str, data: dict[str, str]) -> dict[str, Any]:
        """Generate ConfigMap manifest."""
        return {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": f"{name}-config",
                "namespace": self.namespace,
                "labels": {
                    "app.kubernetes.io/name": name,
                    "app.kubernetes.io/component": "config",
                },
            },
            "data": data,
        }

    def generate_secret(self, name: str, data: dict[str, str]) -> dict[str, Any]:
        """Generate Secret manifest."""
        # Base64 encode secret values
        encoded_data = {}
        for key, value in data.items():
            encoded_data[key] = base64.b64encode(value.encode()).decode()

        return {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": f"{name}-secrets",
                "namespace": self.namespace,
                "labels": {
                    "app.kubernetes.io/name": name,
                    "app.kubernetes.io/component": "secrets",
                },
            },
            "type": "Opaque",
            "data": encoded_data,
        }

    def generate_deployment(
        self,
        config: ServiceConfig,
        strategy: DeploymentStrategy = DeploymentStrategy.ROLLING_UPDATE,
    ) -> dict[str, Any]:
        """Generate Deployment manifest."""

        # Build container spec
        container_spec = {
            "name": config.name,
            "image": (
                f"{self.registry}/{config.full_image}" if self.registry else config.full_image
            ),
            "ports": [{"containerPort": config.target_port, "protocol": "TCP"}],
            "resources": {
                "requests": {
                    "cpu": config.resources.cpu_request,
                    "memory": config.resources.memory_request,
                },
                "limits": {
                    "cpu": config.resources.cpu_limit,
                    "memory": config.resources.memory_limit,
                    "ephemeral-storage": config.resources.ephemeral_storage_limit,
                },
            },
            "readinessProbe": {
                "httpGet": {
                    "path": config.health_check.readiness_path,
                    "port": config.target_port,
                },
                "initialDelaySeconds": config.health_check.initial_delay,
                "timeoutSeconds": config.health_check.timeout,
                "periodSeconds": config.health_check.period,
                "failureThreshold": config.health_check.failure_threshold,
                "successThreshold": config.health_check.success_threshold,
            },
            "livenessProbe": {
                "httpGet": {
                    "path": config.health_check.liveness_path,
                    "port": config.target_port,
                },
                "initialDelaySeconds": config.health_check.initial_delay * 2,
                "timeoutSeconds": config.health_check.timeout,
                "periodSeconds": config.health_check.period,
                "failureThreshold": config.health_check.failure_threshold,
            },
            "startupProbe": {
                "httpGet": {
                    "path": config.health_check.startup_path,
                    "port": config.target_port,
                },
                "initialDelaySeconds": 10,
                "timeoutSeconds": config.health_check.timeout,
                "periodSeconds": 5,
                "failureThreshold": 30,
            },
        }

        # Add environment variables
        env_vars = []
        for key, value in config.environment.items():
            env_vars.append({"name": key, "value": value})

        # Add secrets as environment variables
        for key in config.secrets.keys():
            env_vars.append(
                {
                    "name": key,
                    "valueFrom": {"secretKeyRef": {"name": f"{config.name}-secrets", "key": key}},
                }
            )

        # Add config maps as environment variables
        for key in config.config_maps.keys():
            env_vars.append(
                {
                    "name": key,
                    "valueFrom": {"configMapKeyRef": {"name": f"{config.name}-config", "key": key}},
                }
            )

        if env_vars:
            container_spec["env"] = env_vars

        # Add volume mounts
        if config.volumes:
            volume_mounts = []
            for volume in config.volumes:
                volume_mounts.append({"name": volume["name"], "mountPath": volume["mountPath"]})
            container_spec["volumeMounts"] = volume_mounts

        # Build deployment spec
        deployment_spec = {
            "replicas": config.replicas,
            "selector": {"matchLabels": {"app": config.name, "version": "v1"}},
            "template": {
                "metadata": {
                    "labels": {
                        "app": config.name,
                        "version": "v1",
                        "app.kubernetes.io/name": config.name,
                        "app.kubernetes.io/version": config.tag,
                    }
                },
                "spec": {"containers": [container_spec]},
            },
        }

        # Add strategy
        if strategy == DeploymentStrategy.ROLLING_UPDATE:
            deployment_spec["strategy"] = {
                "type": "RollingUpdate",
                "rollingUpdate": {"maxSurge": 1, "maxUnavailable": 0},
            }
        elif strategy == DeploymentStrategy.RECREATE:
            deployment_spec["strategy"] = {"type": "Recreate"}

        # Add volumes
        if config.volumes:
            volumes = []
            for volume in config.volumes:
                if volume["type"] == "pvc":
                    volumes.append(
                        {
                            "name": volume["name"],
                            "persistentVolumeClaim": {"claimName": volume["claimName"]},
                        }
                    )
                elif volume["type"] == "configMap":
                    volumes.append(
                        {
                            "name": volume["name"],
                            "configMap": {"name": volume["configMapName"]},
                        }
                    )
            deployment_spec["template"]["spec"]["volumes"] = volumes

        # Add service mesh annotations if enabled
        if config.service_mesh:
            annotations = deployment_spec["template"]["metadata"].setdefault("annotations", {})
            annotations.update(
                {
                    "sidecar.istio.io/inject": "true",
                    "prometheus.io/scrape": "true",
                    "prometheus.io/port": str(config.target_port),
                    "prometheus.io/path": "/metrics",
                }
            )

        return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": config.name,
                "namespace": self.namespace,
                "labels": {
                    "app": config.name,
                    "app.kubernetes.io/name": config.name,
                    "app.kubernetes.io/component": "backend",
                },
            },
            "spec": deployment_spec,
        }

    def generate_service(self, config: ServiceConfig) -> dict[str, Any]:
        """Generate Service manifest."""
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": f"{config.name}-service",
                "namespace": self.namespace,
                "labels": {
                    "app": config.name,
                    "app.kubernetes.io/name": config.name,
                    "app.kubernetes.io/component": "service",
                },
            },
            "spec": {
                "type": config.service_type.value,
                "ports": [
                    {
                        "port": config.port,
                        "targetPort": config.target_port,
                        "protocol": "TCP",
                        "name": "http",
                    }
                ],
                "selector": {"app": config.name},
            },
        }

    def generate_hpa(self, config: ServiceConfig) -> dict[str, Any]:
        """Generate HorizontalPodAutoscaler manifest."""
        return {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {
                "name": f"{config.name}-hpa",
                "namespace": self.namespace,
                "labels": {
                    "app": config.name,
                    "app.kubernetes.io/name": config.name,
                    "app.kubernetes.io/component": "autoscaler",
                },
            },
            "spec": {
                "scaleTargetRef": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "name": config.name,
                },
                "minReplicas": config.autoscaling.min_replicas,
                "maxReplicas": config.autoscaling.max_replicas,
                "metrics": [
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "cpu",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": config.autoscaling.target_cpu_utilization,
                            },
                        },
                    },
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "memory",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": config.autoscaling.target_memory_utilization,
                            },
                        },
                    },
                ],
                "behavior": {
                    "scaleUp": {
                        "stabilizationWindowSeconds": config.autoscaling.scale_up_stabilization
                    },
                    "scaleDown": {
                        "stabilizationWindowSeconds": config.autoscaling.scale_down_stabilization
                    },
                },
            },
        }

    def generate_ingress(self, config: ServiceConfig, tls_enabled: bool = True) -> dict[str, Any]:
        """Generate Ingress manifest."""
        ingress_spec = {
            "rules": [
                {
                    "host": config.ingress_host,
                    "http": {
                        "paths": [
                            {
                                "path": config.ingress_path,
                                "pathType": "Prefix",
                                "backend": {
                                    "service": {
                                        "name": f"{config.name}-service",
                                        "port": {"number": config.port},
                                    }
                                },
                            }
                        ]
                    },
                }
            ]
        }

        if tls_enabled and config.ingress_host:
            ingress_spec["tls"] = [
                {"hosts": [config.ingress_host], "secretName": f"{config.name}-tls"}
            ]

        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": f"{config.name}-ingress",
                "namespace": self.namespace,
                "labels": {
                    "app": config.name,
                    "app.kubernetes.io/name": config.name,
                    "app.kubernetes.io/component": "ingress",
                },
                "annotations": {
                    "nginx.ingress.kubernetes.io/rewrite-target": "/",
                    "nginx.ingress.kubernetes.io/ssl-redirect": "true",
                    "cert-manager.io/cluster-issuer": "letsencrypt-prod",
                },
            },
            "spec": ingress_spec,
        }

    def generate_pv(self, name: str, size: str, storage_class: str = "fast-ssd") -> dict[str, Any]:
        """Generate PersistentVolume manifest."""
        return {
            "apiVersion": "v1",
            "kind": "PersistentVolume",
            "metadata": {
                "name": f"{name}-pv",
                "labels": {
                    "app.kubernetes.io/name": name,
                    "app.kubernetes.io/component": "storage",
                },
            },
            "spec": {
                "capacity": {"storage": size},
                "accessModes": ["ReadWriteOnce"],
                "storageClassName": storage_class,
                "hostPath": {"path": f"/data/{name}"},
            },
        }

    def generate_pvc(self, name: str, size: str, storage_class: str = "fast-ssd") -> dict[str, Any]:
        """Generate PersistentVolumeClaim manifest."""
        return {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": f"{name}-pvc",
                "namespace": self.namespace,
                "labels": {
                    "app.kubernetes.io/name": name,
                    "app.kubernetes.io/component": "storage",
                },
            },
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "storageClassName": storage_class,
                "resources": {"requests": {"storage": size}},
            },
        }


class KubernetesDeployer:
    """Deploys and manages Kubernetes resources."""

    def __init__(self, kubeconfig_path: str = None):
        self.kubeconfig_path = kubeconfig_path or os.path.expanduser("~/.kube/config")
        self.kubectl_cmd = self._get_kubectl_cmd()

    def _get_kubectl_cmd(self) -> list[str]:
        """Get kubectl command with kubeconfig."""
        cmd = ["kubectl"]
        if self.kubeconfig_path and os.path.exists(self.kubeconfig_path):
            cmd.extend(["--kubeconfig", self.kubeconfig_path])
        return cmd

    def apply_manifest(self, manifest: dict[str, Any]) -> bool:
        """Apply a single manifest."""
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                yaml.dump(manifest, f, default_flow_style=False)
                f.flush()

                cmd = self.kubectl_cmd + ["apply", "-f", f.name]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    logger.info(f"Applied {manifest['kind']}/{manifest['metadata']['name']}")
                    return True
                else:
                    logger.error(f"Failed to apply manifest: {result.stderr}")
                    return False

        except Exception as e:
            logger.error(f"Error applying manifest: {e}")
            return False
        finally:
            if "f" in locals():
                os.unlink(f.name)

    def apply_manifests(self, manifests: list[dict[str, Any]]) -> bool:
        """Apply multiple manifests."""
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                for i, manifest in enumerate(manifests):
                    if i > 0:
                        f.write("---\n")
                    yaml.dump(manifest, f, default_flow_style=False)
                f.flush()

                cmd = self.kubectl_cmd + ["apply", "-f", f.name]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    logger.info(f"Applied {len(manifests)} manifests")
                    return True
                else:
                    logger.error(f"Failed to apply manifests: {result.stderr}")
                    return False

        except Exception as e:
            logger.error(f"Error applying manifests: {e}")
            return False
        finally:
            if "f" in locals():
                os.unlink(f.name)

    def delete_resource(self, kind: str, name: str, namespace: str = None) -> bool:
        """Delete a Kubernetes resource."""
        try:
            cmd = self.kubectl_cmd + ["delete", kind, name]
            if namespace:
                cmd.extend(["-n", namespace])

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Deleted {kind}/{name}")
                return True
            else:
                logger.error(f"Failed to delete {kind}/{name}: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error deleting resource: {e}")
            return False

    def get_resource_status(self, kind: str, name: str, namespace: str = None) -> dict[str, Any]:
        """Get status of a Kubernetes resource."""
        try:
            cmd = self.kubectl_cmd + ["get", kind, name, "-o", "json"]
            if namespace:
                cmd.extend(["-n", namespace])

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {"error": result.stderr}

        except Exception as e:
            logger.error(f"Error getting resource status: {e}")
            return {"error": str(e)}

    def scale_deployment(self, name: str, replicas: int, namespace: str = None) -> bool:
        """Scale a deployment."""
        try:
            cmd = self.kubectl_cmd + [
                "scale",
                "deployment",
                name,
                f"--replicas={replicas}",
            ]
            if namespace:
                cmd.extend(["-n", namespace])

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Scaled deployment {name} to {replicas} replicas")
                return True
            else:
                logger.error(f"Failed to scale deployment: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error scaling deployment: {e}")
            return False

    def rollout_restart(self, name: str, namespace: str = None) -> bool:
        """Restart a deployment."""
        try:
            cmd = self.kubectl_cmd + ["rollout", "restart", "deployment", name]
            if namespace:
                cmd.extend(["-n", namespace])

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Restarted deployment {name}")
                return True
            else:
                logger.error(f"Failed to restart deployment: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error restarting deployment: {e}")
            return False


class TQGenAIKubernetesOrchestrator:
    """Complete Kubernetes orchestration for TQ GenAI Chat."""

    def __init__(self, namespace: str = "tq-genai-chat", registry: str = ""):
        self.namespace = namespace
        self.registry = registry
        self.generator = KubernetesManifestGenerator(namespace, registry)
        self.deployer = KubernetesDeployer()

        # Service configurations
        self.services = self._get_service_configs()

    def _get_service_configs(self) -> dict[str, ServiceConfig]:
        """Get default service configurations."""
        return {
            "main-app": ServiceConfig(
                name="main-app",
                image="tq-genai-chat/main",
                port=5000,
                target_port=5000,
                replicas=3,
                service_type=ServiceType.CLUSTER_IP,
                ingress=True,
                ingress_host="chat.example.com",
                environment={"FLASK_ENV": "production", "LOG_LEVEL": "INFO"},
                secrets={
                    "OPENAI_API_KEY": "",
                    "ANTHROPIC_API_KEY": "",
                    "GROQ_API_KEY": "",
                    "SECRET_KEY": "",
                },
                volumes=[
                    {
                        "name": "uploads",
                        "type": "pvc",
                        "claimName": "uploads-pvc",
                        "mountPath": "/app/uploads",
                    }
                ],
            ),
            "chat-service": ServiceConfig(
                name="chat-service",
                image="tq-genai-chat/chat-service",
                port=8001,
                target_port=8001,
                replicas=5,
                autoscaling=AutoScalingConfig(
                    min_replicas=3, max_replicas=20, target_cpu_utilization=60
                ),
                resources=ResourceRequirements(
                    cpu_request="200m",
                    cpu_limit="1000m",
                    memory_request="256Mi",
                    memory_limit="1Gi",
                ),
            ),
            "file-service": ServiceConfig(
                name="file-service",
                image="tq-genai-chat/file-service",
                port=8002,
                target_port=8002,
                replicas=3,
                autoscaling=AutoScalingConfig(
                    min_replicas=2, max_replicas=10, target_cpu_utilization=70
                ),
                resources=ResourceRequirements(
                    cpu_request="300m",
                    cpu_limit="1500m",
                    memory_request="512Mi",
                    memory_limit="2Gi",
                ),
                volumes=[
                    {
                        "name": "file-storage",
                        "type": "pvc",
                        "claimName": "file-storage-pvc",
                        "mountPath": "/app/storage",
                    }
                ],
            ),
            "redis": ServiceConfig(
                name="redis",
                image="redis",
                tag="7-alpine",
                port=6379,
                target_port=6379,
                replicas=1,
                resources=ResourceRequirements(
                    cpu_request="100m",
                    cpu_limit="500m",
                    memory_request="256Mi",
                    memory_limit="512Mi",
                ),
                volumes=[
                    {
                        "name": "redis-data",
                        "type": "pvc",
                        "claimName": "redis-data-pvc",
                        "mountPath": "/data",
                    }
                ],
            ),
        }

    def generate_all_manifests(self) -> list[dict[str, Any]]:
        """Generate all Kubernetes manifests."""
        manifests = []

        # Namespace
        manifests.append(self.generator.generate_namespace())

        # Persistent Volumes and Claims
        manifests.extend(
            [
                self.generator.generate_pvc("uploads", "10Gi"),
                self.generator.generate_pvc("file-storage", "50Gi"),
                self.generator.generate_pvc("redis-data", "5Gi"),
            ]
        )

        # Services
        for service_name, config in self.services.items():
            # Secrets
            if config.secrets:
                manifests.append(self.generator.generate_secret(service_name, config.secrets))

            # ConfigMaps
            if config.config_maps:
                manifests.append(
                    self.generator.generate_configmap(service_name, config.config_maps)
                )

            # Deployment
            manifests.append(self.generator.generate_deployment(config))

            # Service
            manifests.append(self.generator.generate_service(config))

            # HPA (if replicas > 1)
            if config.replicas > 1:
                manifests.append(self.generator.generate_hpa(config))

            # Ingress (if enabled)
            if config.ingress:
                manifests.append(self.generator.generate_ingress(config))

        return manifests

    def deploy(self, apply: bool = True) -> bool:
        """Deploy the entire application stack."""
        try:
            manifests = self.generate_all_manifests()

            if apply:
                return self.deployer.apply_manifests(manifests)
            else:
                # Just generate YAML files
                output_dir = Path("k8s-manifests")
                output_dir.mkdir(exist_ok=True)

                for i, manifest in enumerate(manifests):
                    kind = manifest["kind"].lower()
                    name = manifest["metadata"]["name"]
                    filename = f"{i:02d}-{kind}-{name}.yaml"

                    with open(output_dir / filename, "w") as f:
                        yaml.dump(manifest, f, default_flow_style=False)

                logger.info(f"Generated {len(manifests)} manifests in {output_dir}")
                return True

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return False

    def update_service(self, service_name: str, **kwargs) -> bool:
        """Update a service configuration and redeploy."""
        if service_name not in self.services:
            logger.error(f"Service {service_name} not found")
            return False

        config = self.services[service_name]

        # Update configuration
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        # Generate and apply updated manifests
        manifests = [
            self.generator.generate_deployment(config),
            self.generator.generate_service(config),
        ]

        if config.replicas > 1:
            manifests.append(self.generator.generate_hpa(config))

        return self.deployer.apply_manifests(manifests)

    def scale_service(self, service_name: str, replicas: int) -> bool:
        """Scale a service."""
        if service_name not in self.services:
            logger.error(f"Service {service_name} not found")
            return False

        return self.deployer.scale_deployment(service_name, replicas, self.namespace)

    def get_cluster_status(self) -> dict[str, Any]:
        """Get status of all deployed resources."""
        status = {
            "namespace": self.namespace,
            "services": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        for service_name in self.services.keys():
            service_status = {}

            # Deployment status
            deployment_status = self.deployer.get_resource_status(
                "deployment", service_name, self.namespace
            )
            service_status["deployment"] = deployment_status

            # Service status
            svc_status = self.deployer.get_resource_status(
                "service", f"{service_name}-service", self.namespace
            )
            service_status["service"] = svc_status

            # HPA status (if exists)
            hpa_status = self.deployer.get_resource_status(
                "hpa", f"{service_name}-hpa", self.namespace
            )
            if "error" not in hpa_status:
                service_status["hpa"] = hpa_status

            status["services"][service_name] = service_status

        return status

    def cleanup(self) -> bool:
        """Clean up all deployed resources."""
        try:
            return self.deployer.delete_resource("namespace", self.namespace)
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return False


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TQ GenAI Chat Kubernetes Orchestrator")
    parser.add_argument("--namespace", default="tq-genai-chat", help="Kubernetes namespace")
    parser.add_argument("--registry", default="", help="Container registry")
    parser.add_argument("--deploy", action="store_true", help="Deploy to cluster")
    parser.add_argument("--generate-only", action="store_true", help="Generate manifests only")
    parser.add_argument("--status", action="store_true", help="Get cluster status")
    parser.add_argument("--cleanup", action="store_true", help="Clean up resources")
    parser.add_argument("--scale", nargs=2, metavar=("SERVICE", "REPLICAS"), help="Scale service")

    args = parser.parse_args()

    orchestrator = TQGenAIKubernetesOrchestrator(args.namespace, args.registry)

    if args.deploy:
        success = orchestrator.deploy(apply=True)
    elif args.generate_only:
        success = orchestrator.deploy(apply=False)
    elif args.status:
        status = orchestrator.get_cluster_status()
    elif args.cleanup:
        success = orchestrator.cleanup()
    elif args.scale:
        service_name, replicas = args.scale
        success = orchestrator.scale_service(service_name, int(replicas))
    else:
        parser.print_help()
