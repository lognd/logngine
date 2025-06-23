#pragma once

#include <vector>
#include <array>
#include <chrono>
#include <optional>
#include <variant>
#include <memory>
#include <queue>

namespace logngine::core
{
    // compile time functions just for computed minimum split size.
    consteval size_t ceval_min(const size_t a, const size_t b) { return a < b ? a : b; }
    consteval size_t ceval_max(const size_t a, const size_t b) { return a > b ? a : b; }
    constexpr double inf = std::numeric_limits<double>::infinity();

    // ==========================================================
    //  R*-Tree (w/ traversal) implementation
    // ==========================================================

    // ----------------------------------------------------------
    //  R*-Tree Bounding Regions
    // ----------------------------------------------------------
    template <size_t D>
    struct MinimumBoundingRegion
    {
        MinimumBoundingRegion();
        explicit MinimumBoundingRegion(const std::array<double, D>& point): min(point), max(point) {};

        std::array<double, D> min;
        std::array<double, D> max;

        bool contains(const std::array<double, D>& point) const;
        bool overlaps(const MinimumBoundingRegion& other) const;
        void expand(const std::array<double, D>& point);
        void expand(const MinimumBoundingRegion& region);
        [[nodiscard]] double area() const;
    };
    template <size_t D>
    using MBR = MinimumBoundingRegion<D>;

    // ----------------------------------------------------------
    //  R*-Tree Nodes
    // ----------------------------------------------------------

    template <size_t D, size_t N, size_t L, typename S>
    struct RSTInternalNode;
    template <size_t D, size_t N, size_t L, typename S>
    struct RSTLeafNode;
    template <size_t D, size_t N, size_t L, typename S>
    using RSTNode = std::variant<RSTInternalNode<D, N, L, S>, RSTLeafNode<D, N, L, S>>;
    template <typename STORED_DATA_TYPE, size_t D_REGION, size_t N_CHILD, size_t N_KEYS = N_CHILD>
    class RSTTree;

    // For splitting logic later on.
    template <size_t D, size_t N, size_t L, typename S>
    struct SplitResult
    {
        MBR<D> new_region;
        std::unique_ptr<RSTNode<D, N, L, S>> sibling;
    };
    template <size_t D, typename S>
    struct SplitEntry
    {
        MBR<D> region;
        S value;
    };
    struct SplitTracker
    {
        size_t axis = 0;
        size_t location = 0;

        double overlap = inf;
        double margin = inf;
        double area = inf;

        void update(size_t axis, size_t location, double overlap, double margin, double area);
    };

    // MBR-Node helper functions
    template <size_t D>
    double compute_overlap(MBR<D> A, MBR<D> B);
    template <size_t D>
    double compute_margin(MBR<D> A, MBR<D> B);
    template <size_t D>
    double compute_area(MBR<D> A, MBR<D> B);

    namespace RSTNodeFN
    {
        template <size_t D, size_t N, size_t L, typename S>
        [[nodiscard]] bool is_leaf(const RSTNode<D, N, L, S>& node);
        template <size_t D, size_t N, size_t L, typename S>
        [[nodiscard]] size_t get_size(const RSTNode<D, N, L, S>& node);
        template <size_t D, size_t N, size_t L, typename S>
        [[nodiscard]] bool is_full(const RSTNode<D, N, L, S>& node);
        template <size_t D, size_t N, size_t L, typename S>
        [[nodiscard]] std::optional<SplitResult<D, N, L, S>> insert(RSTNode<D, N, L, S>& node, const std::array<double, D>& key, const S& value);
    }

    template <size_t D_REGION, size_t N_CHILD, size_t N_KEYS, typename STORED_DATA_TYPE>
    struct RSTInternalNode
    {
        constexpr static size_t MIN_SPLIT_COUNT = ceval_max(static_cast<size_t> (RSTTree<STORED_DATA_TYPE, D_REGION, N_CHILD>::MIN_SPLIT * N_CHILD), 1);

        size_t size = 0;
        MBR<D_REGION> region{};
        std::array<std::optional<MBR<D_REGION>>, N_CHILD> subregions{};
        std::array<std::unique_ptr<RSTNode<D_REGION, N_CHILD, N_KEYS, STORED_DATA_TYPE>>, N_CHILD> children{};

        std::optional<SplitResult<D_REGION, N_CHILD, N_KEYS, STORED_DATA_TYPE>> insert(const std::array<double, D_REGION>& key, const STORED_DATA_TYPE& value);
        [[nodiscard]] bool is_full() const { return this->size == N_CHILD; }
    };
    template <size_t D_REGION, size_t N_CHILD, size_t N_KEYS, typename STORED_DATA_TYPE>
    struct RSTLeafNode
    {
        RSTLeafNode(const size_t size, const MBR<D_REGION>& region, std::array<std::optional<MBR<D_REGION>>, N_KEYS+1> subregions,
            std::array<std::optional<STORED_DATA_TYPE>, N_KEYS+1> children): size(size), region(region), subregions(std::move(subregions)), children(std::move(children)) {}
        constexpr static size_t MIN_SPLIT_COUNT = ceval_max(static_cast<size_t> (RSTTree<STORED_DATA_TYPE, D_REGION, N_CHILD, N_KEYS>::MIN_SPLIT * N_CHILD), 1);

        size_t size = 0;
        MBR<D_REGION> region{};
        std::array<std::optional<MBR<D_REGION>>, N_KEYS> subregions{};
        std::array<std::optional<STORED_DATA_TYPE>, N_KEYS> children{};

        std::optional<SplitResult<D_REGION, N_CHILD, N_KEYS, STORED_DATA_TYPE>> insert(const std::array<double, D_REGION>& key, const STORED_DATA_TYPE& value);
        [[nodiscard]] bool is_full() const { return this->size == N_KEYS; }
    };

    // ----------------------------------------------------------
    //  R*-Tree Implementation
    // ----------------------------------------------------------
    template <typename STORED_DATA_TYPE, size_t D_REGION, size_t N_CHILD, size_t N_KEYS = N_CHILD>
    class RSTTree
    {
    public:

        constexpr static double MIN_SPLIT = 0.25;

        bool insert(const std::array<double, D_REGION>& key, const STORED_DATA_TYPE& value);
        bool remove(const std::array<double, D_REGION>& key);
        std::vector<STORED_DATA_TYPE> query(const std::array<double, D_REGION>& key, size_t max = 1) const;

    private:
        std::unique_ptr<RSTNode<D_REGION, N_CHILD, N_KEYS, STORED_DATA_TYPE>> root = nullptr;
    };
}
