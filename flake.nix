{
  description = "OpenDomains dev environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            buildInputs = with pkgs; [
              python3
              python3Packages.pip
              python3Packages.virtualenv
            ];

            shellHook = ''
              if [ ! -d .venv ]; then
                echo "Creating venv..."
                python -m venv .venv
              fi
              source .venv/bin/activate
              echo "Python venv activated. Run 'pip install -r requirements.txt' if needed."
            '';
          };
        }
      );
    };
}
