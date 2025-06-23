#include <logngine/core/RSTTree.h>
#include <algorithm>
#include <limits>
#include <stdexcept>

namespace logngine::core
{
    // ==========================================================
    //  R*-Tree (w/ traversal) implementation
    // ==========================================================

    // ----------------------------------------------------------
    //  R*-Tree Bounding Regions
    // ----------------------------------------------------------
#pragma region MBR
    template <size_t D>
    MinimumBoundingRegion<D>::MinimumBoundingRegion()
    {
        this->max.fill(-inf);
        this->min.fill(inf);
    }
    template <size_t D>
    double MinimumBoundingRegion<D>::area() const
    {
        double result = 1.0;
        for (size_t i = 0; i < D; ++i) result *= (this->max[i] - this->min[i]);
        return result;
    }
    template <size_t D>
    bool MinimumBoundingRegion<D>::contains(const std::array<double, D>& point) const
    {
        for (size_t i = 0; i < D; ++i)
            if (point[i] < this->min[i] || point[i] > this->max[i]) return false;
        return true;
    }
    template <size_t D>
    bool MinimumBoundingRegion<D>::overlaps(const MinimumBoundingRegion& other) const
    {
        // Separating axis theorem
        for (size_t i = 0; i < D; ++i) if (this->max[i] < other.min[i] || this->min[i] > other.max[i]) return false;
        return true;
    }
    template <size_t D>
    void MinimumBoundingRegion<D>::expand(const MinimumBoundingRegion& region)
    {
        for (size_t i = 0; i < D; ++i)
        {
            if (region.min[i] < this->min[i]) this->min[i] = region.min[i];
            if (region.max[i] > this->max[i]) this->max[i] = region.max[i];
        }
    }
    template <size_t D>
    void MinimumBoundingRegion<D>::expand(const std::array<double, D>& point)
    {
        for (size_t i = 0; i < D; ++i)
        {
            if (point[i] < this->min[i]) this->min[i] = point[i];
            if (point[i] > this->max[i]) this->max[i] = point[i];
        }
    }
#pragma endregion

#pragma region MBR Helper Functions
    void SplitTracker::update(const size_t axis, const size_t location, const double overlap, const double margin, const double area)
    {
        this->axis = axis;
        this->location = location;
        this->overlap = overlap;
        this->margin = margin;
        this->area = area;
    }

    template <size_t D>
    double compute_overlap(MBR<D> A, MBR<D> B)
    {
        double volume = 1.0;
        for (size_t i = 0; i < D; ++i)
        {
            const double overlap = std::min(A.max[i], B.max[i]) - std::max(A.min[i], B.min[i]);
            if (overlap <= 0.0) return 0.0;
            volume *= overlap;
        }
        return volume;
    }
    template <size_t D>
    double compute_margin(MBR<D> A, MBR<D> B)
    {
        double sum = 0.0;
        for (size_t i = 0; i < D; ++i) sum += (A.max[i] - A.min[i]) + (B.max[i] - B.min[i]);
        return 2.0 * sum;
    }
    template <size_t D>
    double compute_area(MBR<D> A, MBR<D> B)
    {
        return A.area() + B.area();
    }
#pragma endregion

    // ----------------------------------------------------------
    //  R*-Tree Node
    // ----------------------------------------------------------
#pragma region Node
    namespace RSTNodeFN
    {
        template <size_t D, size_t N, size_t L, typename S>
        bool is_leaf(const RSTNode<D, N, L, S>& node){ return std::holds_alternative<RSTLeafNode<D, N, L, S>>(node); }
        template <size_t D, size_t N, size_t L, typename S>
        size_t get_size(const RSTNode<D, N, L, S>& node)
        {
            if (auto* internal = std::get_if<RSTInternalNode<D, N, L, S>>(&node)) { return internal->size; }
            if (auto* leaf = std::get_if<RSTLeafNode<D, N, L, S>>(&node)) { return leaf->size; }
            throw std::runtime_error("Did not receive an RSTNode in get_size...");
        }
        template <size_t D, size_t N, size_t L, typename S>
        bool is_full(const RSTNode<D, N, L, S>& node)
        {
            if (auto* internal = std::get_if<RSTInternalNode<D, N, L, S>>(&node)) { return internal->is_full(); }
            if (auto* leaf = std::get_if<RSTLeafNode<D, N, L, S>>(&node)) { return leaf->is_full(); }
            throw std::runtime_error("Did not receive an RSTNode in get_size...");
        }
        template <size_t D, size_t N, size_t L, typename S>
        std::optional<SplitResult<D, N, L, S>> insert(RSTNode<D, N, L, S>& node, const std::array<double, D>& key, const S& value)
        {
            if (auto* internal = std::get_if<RSTInternalNode<D, N, L, S>>(&node)) { return internal->insert(key, value); }
            if (auto* leaf = std::get_if<RSTLeafNode<D, N, L, S>>(&node)) { return leaf->insert(key, value); }
            throw std::runtime_error("Did not receive an RSTNode in get_size...");
        }
    }

    // ----------------------------------------------------------
    //  R*-Tree Leaf Nodes
    // ----------------------------------------------------------
    template <size_t D, size_t N, size_t L, typename S>
    std::optional<SplitResult<D, N, L, S>> RSTLeafNode<D, N, L, S>::insert(const std::array<double, D>& key, const S& value)
    {
        if (!is_full())
        {
            this->subregions[size] = key;
            this->children[size] = value;
            this->region.expand(key);

            ++this->size;
            return std::nullopt;
        }

        SplitTracker best_split{};

        std::array<SplitEntry<D, S>, N+1> entries{};
        for (size_t i = 0; i < N; ++i)
        {
            if (!subregions[i].has_value() || !children[i].has_value()) throw std::runtime_error("Corrupt node: missing subregion/child...");
            entries[i] = SplitEntry{*subregions[i], *children[i]};
        }
        entries[N] = SplitEntry<D, S>{MBR<D>(key), value};

        // Iterate through all the axes
        for (size_t axis = 0; axis < D; ++axis)
        {
            std::sort(entries.begin(), entries.end(),
               [axis](const SplitEntry<D, S>& a, const SplitEntry<D, S>& b) -> bool { return a.region.min[axis] < b.region.min[axis]; }
               );

            for (size_t k = MIN_SPLIT_COUNT; k < L + 1 - MIN_SPLIT_COUNT; ++k)
            {
                MBR<D> lower{}, upper{};

                for (size_t j = 0; j < k; ++j) lower.expand(entries[j].region);
                for (size_t j = k; j < L + 1; ++j) upper.expand(entries[j].region);

                const double overlap = compute_overlap(lower, upper);

                if (overlap > best_split.overlap) continue;

                const double margin = compute_margin(lower, upper);
                const double area = compute_area(lower, upper);

                if (overlap < best_split.overlap)
                {
                    best_split.update(axis, k, overlap, margin, area);
                    continue;
                }

                if (margin > best_split.margin) continue;
                if (margin < best_split.margin)
                {
                    best_split.update(axis, k, overlap, margin, area);
                    continue;
                }

                if (area > best_split.area) continue;
                if (area < best_split.area) best_split.update(axis, k, overlap, margin, area);
            }
        }

        if (best_split.overlap == inf) throw std::runtime_error("Somehow received an empty full RSTLeafNode...");

        // Return the best result found
        std::sort(entries.begin(), entries.end(),
               [&best_split](const SplitEntry<D, S>& a, const SplitEntry<D, S>& b) -> bool { return a.region.min[best_split.axis] < b.region.min[best_split.axis]; }
               );

        MBR<D> lower{}, upper{};
        std::array<std::optional<MBR<D>>, L+1> lower_subregions{};
        std::array<std::optional<S>, L+1> lower_children{};
        for (size_t j = 0; j < best_split.location; ++j)
        {
            lower.expand(entries[j].region);
            lower_subregions[j] = std::move(entries[j].region);
            lower_children[j] = std::move(entries[j].value);
        }

        std::array<std::optional<MBR<D>>, L+1> upper_subregions{};
        std::array<std::optional<S>, L+1> upper_children{};
        for (size_t j = best_split.location; j < L + 1; ++j)
        {
            upper.expand(entries[j].region);
            upper_subregions[j] = std::move(entries[j].region);
            upper_children[j] = std::move(entries[j].value);
        }

        // Lower split replaces the parent;
        this->region = std::move(lower);
        this->size = best_split.location;
        this->subregions = std::move(lower_subregions);
        this->children = std::move(lower_children);

        std::unique_ptr<RSTLeafNode> sibling = std::make_unique<RSTLeafNode>(
            L + 1 - best_split.location,
            upper,
            std::move(upper_subregions),
            std::move(upper_children)
            );

        return {upper, std::move(sibling)};
    }

    // ----------------------------------------------------------
    //  R*-Tree Internal Nodes
    // ----------------------------------------------------------
    template <size_t D, size_t N, size_t L, typename S>
    std::optional<SplitResult<D, N, L, S>> RSTInternalNode<D, N, L, S>::insert(const std::array<double, D>& key, const S& value)
    {
        if (!is_full())
        {
            // TODO: come back here
        }
    }

#pragma endregion



}
